import asyncio
from collections.abc import Callable
from datetime import timedelta
from typing import cast

import pytest
import strawberry
import test_rest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from korpa_api.gql.limits import extensions
from korpa_api.gql.router import make_router
from korpa_api.main import app, lifespan
from korpa_ingest import db
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from test_rest import AS_OF, B1, B2
from test_rest import engine as engine

rest_client = test_rest.client


@pytest.fixture()
def client(rest_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("korpa_api.gql.context.belgrade_today", lambda: AS_OF)
    return rest_client


def test_product_price_cheapest_and_source_date(client: TestClient) -> None:
    response = client.post(
        "/graphql",
        json={
            "query": """
        query($code: String!) {
          asOf
          product(barcode: $code) {
            barcode name brand unit category { code name }
            prices { regularPara discountedPara effectivePara unitPricePara vat
                     discountFrom discountTo listDate asOf
                     format { id name retailer { name slug } } }
            cheapest { effectivePara format { id } }
          }
        }
    """,
            "variables": {"code": B1},
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["asOf"] == AS_OF.isoformat()
    assert response.json()["extensions"]["as_of"] == AS_OF.isoformat()
    assert data["product"]["category"] == {"code": 1, "name": "Hrana"}
    assert [p["effectivePara"] for p in data["product"]["prices"]] == [80, 105, 10]
    assert all(p["listDate"] and p["asOf"] == AS_OF.isoformat() for p in data["product"]["prices"])
    assert data["product"]["cheapest"] == {"effectivePara": 10, "format": {"id": 3}}


@pytest.mark.parametrize(
    ("start", "end", "discount", "expected"),
    [
        (AS_OF, AS_OF, 70, 70),
        (None, AS_OF, 70, 70),
        (AS_OF, None, 70, 70),
        (None, None, 70, 70),
        (AS_OF + timedelta(1), None, 70, 100),
        (None, AS_OF - timedelta(1), 70, 100),
        (None, None, None, 100),
    ],
)
def test_graphql_uses_shared_effective_price_at_window_edges(
    client: TestClient,
    engine: Engine,
    start: object,
    end: object,
    discount: int | None,
    expected: int,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            db.prices_current.update()
            .where(
                db.prices_current.c.barcode == B2,
            )
            .values(regular=100, discounted=discount, disc_from=start, disc_to=end)
        )
    response = client.post(
        "/graphql",
        json={
            "query": f'{{ product(barcode:"{B2}") '
            "{ prices { effectivePara } cheapest { effectivePara } } }"
        },
    )
    assert response.status_code == 200, response.text
    product = response.json()["data"]["product"]
    assert all(price["effectivePara"] == expected for price in product["prices"])
    assert product["cheapest"]["effectivePara"] == expected


def test_names_history_changes_and_unknown_products(client: TestClient, engine: Engine) -> None:
    with engine.begin() as c:
        c.execute(db.product_names.insert().values(barcode=B1, retailer_id=1, raw_name="MLEKO 1L"))
        c.execute(
            db.monthly_snapshots.insert().values(
                format_id=1, barcode=B1, month=AS_OF.replace(day=1), regular=120, discounted=90
            )
        )
        c.execute(
            db.price_changes.insert().values(format_id=1, barcode=B1, changed_on=AS_OF, regular=100)
        )
    response = client.post(
        "/graphql",
        json={
            "query": f'{{ product(barcode:"{B1}") {{ '
            "names { rawName retailer { slug } } history(months:1) { month regularPara listDate } "
            "changes(days:1) { changedOn regularPara listDate } } "
            'products(barcodes:["0000000000099"]) { barcode } categories { code name } }'
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["products"] == [None]
    assert data["product"]["names"] == [{"rawName": "MLEKO 1L", "retailer": {"slug": "r1"}}]
    assert data["product"]["history"][0]["regularPara"] == 120
    assert data["product"]["history"][0]["listDate"] == AS_OF.replace(day=1).isoformat()
    assert data["product"]["changes"][0]["listDate"] == AS_OF.isoformat()
    assert len(data["categories"]) == 2


@pytest.mark.parametrize(
    "field",
    [
        'product(barcode:"123") { barcode }',
        "products(barcodes:[]) { barcode }",
        f'product(barcode:"{B1}") {{ history(months:25) {{ month }} }}',
        f'product(barcode:"{B1}") {{ history(months:0) {{ month }} }}',
        f'product(barcode:"{B1}") {{ changes(days:121) {{ changedOn }} }}',
        f'product(barcode:"{B1}") {{ changes(days:0) {{ changedOn }} }}',
    ],
)
def test_input_caps_are_problem_json(client: TestClient, field: str) -> None:
    response = client.post("/graphql", json={"query": "{ " + field + " }"})
    assert response.status_code == 422, response.text
    assert response.headers["content-type"] == "application/problem+json"


def test_product_list_cap(client: TestClient) -> None:
    response = client.post(
        "/graphql",
        json={
            "query": "query($codes:[String!]!) { products(barcodes:$codes) { barcode } }",
            "variables": {"codes": [B1] * 51},
        },
    )
    assert response.status_code == 422


def test_introspection_remains_on_and_mutation_is_absent(client: TestClient) -> None:
    response = client.post(
        "/graphql",
        json={
            "query": "{ __schema { queryType { name } mutationType { name } "
            "subscriptionType { name } } }"
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["__schema"] == {
        "queryType": {"name": "Query"},
        "mutationType": None,
        "subscriptionType": None,
    }
    response = client.post("/graphql", json={"query": "mutation { __typename }"})
    assert response.status_code == 400


def test_graphiql_only_in_development(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    assert client.get("/graphql").status_code == 404
    monkeypatch.setenv("ENV", "dev")
    dev = FastAPI(lifespan=lifespan)
    dev.include_router(make_router(), prefix="/graphql")
    with TestClient(dev) as dev_client:
        response = dev_client.get("/graphql", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


def test_alias_limit(client: TestClient) -> None:
    document = "{ " + " ".join(f"a{i}: asOf" for i in range(16)) + " }"
    response = client.post("/graphql", json={"query": document})
    assert response.status_code == 400
    assert "alias" in response.json()["detail"].lower()


def test_token_limit(client: TestClient) -> None:
    document = (
        "{ products(barcodes:[" + ",".join(f'"{B1}"' for _ in range(1001)) + "]) { barcode } }"
    )
    response = client.post("/graphql", json={"query": document})
    assert response.status_code == 400
    assert "token" in response.json()["detail"].lower()


def test_cost_limit_counts_variable_bounds_and_fragments(client: TestClient) -> None:
    response = client.post(
        "/graphql",
        json={
            "query": """
       query($codes:[String!]!, $months:Int!) {
         products(barcodes:$codes) { ...History }
       }
       fragment History on Product { history(months:$months) { month regularPara discountedPara } }
    """,
            "variables": {"codes": [B1] * 20, "months": 24},
        },
    )
    assert response.status_code == 400
    assert "cost" in response.json()["detail"].lower()
    assert "5000" in response.json()["detail"]


@strawberry.type
class DepthNode:
    @strawberry.field
    def next(self) -> "DepthNode":
        return self


@strawberry.type
class DepthQuery:
    @strawberry.field
    def node(self) -> DepthNode:
        return DepthNode()


def test_depth_limit_with_valid_recursive_test_schema() -> None:
    # Exercise the same production extensions with a valid deeper graph, without
    # adding artificial fields to the public API.
    schema = strawberry.Schema(query=DepthQuery, extensions=extensions())
    text = "{ node { " + "next { " * 8 + "__typename" + " }" * 8 + " } }"
    result = asyncio.run(schema.execute(text))
    assert result.errors and "depth" in result.errors[0].message


def test_batching_is_constant_and_request_caches_do_not_leak(
    client: TestClient, engine: Engine, record_property: Callable[[str, object], None]
) -> None:
    codes = [f"{i:013d}" for i in range(1, 21)]
    with engine.begin() as c:
        c.execute(
            db.products.insert(),
            [
                {
                    "barcode": code,
                    "name": f"Proizvod {code}",
                    "brand": "",
                    "unit": "kom",
                    "category_code": 1,
                }
                for code in codes[3:]
            ],
        )
        c.execute(
            db.prices_current.insert(),
            [
                {
                    "format_id": 1,
                    "barcode": code,
                    "regular": 100,
                    "unit_price": 100,
                    "vat": 20,
                    "list_date": AS_OF,
                }
                for code in codes[3:]
            ],
        )
        c.execute(
            db.monthly_snapshots.insert(),
            [
                {"format_id": 1, "barcode": code, "month": AS_OF.replace(day=1), "regular": 100}
                for code in codes
            ],
        )
    async_engine = cast(AsyncEngine, app.state.sessions.kw["bind"])
    statements: list[str] = []

    def count_sql(
        conn: object,
        cursor: object,
        text: str,
        parameters: object,
        execution_context: object,
        executemany: object,
    ) -> None:
        statements.append(text)

    counts = []
    event.listen(async_engine.sync_engine, "before_cursor_execute", count_sql)
    try:
        for n in (1, 20):
            statements.clear()
            response = client.post(
                "/graphql",
                json={
                    "query": """
                query($codes:[String!]!) { products(barcodes:$codes) {
                  prices { format { retailer { name } } } history(months:1) { month }
                } }
            """,
                    "variables": {"codes": codes[:n]},
                },
            )
            assert response.status_code == 200, response.text
            assert len(response.json()["data"]["products"]) == n
            counts.append(len(statements))
        assert counts[0] == counts[1] <= 8
        record_property("sql_statements_one", counts[0])
        record_property("sql_statements_twenty", counts[1])
        with engine.begin() as c:
            c.execute(
                db.prices_current.update()
                .where(db.prices_current.c.barcode == B1)
                .values(
                    regular=1,
                    discounted=None,
                )
            )
        response = client.post(
            "/graphql",
            json={"query": f'{{ product(barcode:"{B1}") {{ cheapest {{ effectivePara }} }} }}'},
        )
        assert response.json()["data"]["product"]["cheapest"]["effectivePara"] == 1
    finally:
        event.remove(async_engine.sync_engine, "before_cursor_execute", count_sql)


@pytest.mark.parametrize("body", [[], {"query": ""}, {"query": "{ asOf }", "variables": []}])
def test_invalid_envelopes(client: TestClient, body: object) -> None:
    response = client.post("/graphql", json=body)
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


def test_history_windows_are_inclusive_and_loader_keys_include_bounds(
    client: TestClient, engine: Engine
) -> None:
    from korpa_api.gql.context import month_start

    months = [month_start(AS_OF, n) for n in (1, 2, 3)]
    days = [AS_OF - timedelta(days=n) for n in (0, 1, 2)]
    with engine.begin() as c:
        c.execute(
            db.monthly_snapshots.insert(),
            [
                {"format_id": 1, "barcode": B1, "month": month, "regular": 100}
                for month in months + [AS_OF.replace(day=1) + timedelta(days=32)]
            ],
        )
        c.execute(
            db.price_changes.insert(),
            [
                {"format_id": 1, "barcode": B1, "changed_on": day, "regular": 100}
                for day in days + [AS_OF + timedelta(days=1)]
            ],
        )
    response = client.get(
        "/graphql",
        params={
            "query": f'''{{ product(barcode:"{B1}") {{
        one: history(months:1) {{ month }} two: history(months:2) {{ month }}
        today: changes(days:1) {{ changedOn }} yesterday: changes(days:2) {{ changedOn }}
    }} }}'''
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "public, max-age=300"
    product = response.json()["data"]["product"]
    assert product["one"] == [{"month": months[0].isoformat()}]
    assert product["two"] == [{"month": month.isoformat()} for month in months[:2]]
    assert product["today"] == [{"changedOn": days[0].isoformat()}]
    assert product["yesterday"] == [{"changedOn": day.isoformat()} for day in days[:2]]


def test_over_cap_price_lists_are_rejected_without_truncation(
    client: TestClient, engine: Engine
) -> None:
    with engine.begin() as c:
        c.execute(
            db.retail_formats.insert(),
            [{"id": n, "retailer_id": 1, "name": f"Format {n}"} for n in range(5, 63)],
        )
        c.execute(
            db.prices_current.insert(),
            [
                {
                    "format_id": n,
                    "barcode": B1,
                    "regular": 100,
                    "unit_price": 100,
                    "vat": 20,
                    "list_date": AS_OF,
                }
                for n in range(5, 63)
            ],
        )
    response = client.post(
        "/graphql",
        json={"query": f'{{ product(barcode:"{B1}") {{ prices {{ effectivePara }} }} }}'},
    )
    assert response.status_code == 422, response.text
    assert "60-record limit" in response.json()["detail"]
    assert "data" not in response.json()


def test_schema_export_contains_rest_paths_without_graphql() -> None:
    import json
    import tempfile

    # Exporting must include FastAPI's lazily included REST routers.
    from pathlib import Path

    from korpa_api.export_openapi import export

    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "openapi.json"
        export(target)
        paths = json.loads(target.read_text(encoding="utf-8"))["paths"]
    assert set(paths) == {
        "/health",
        "/api/search",
        "/api/basket",
        "/api/categories",
        "/api/quality",
        "/api/index",
        "/api/signals",
    }


def test_monthly_prices_join_compacted_and_live_months(client: TestClient, engine: Engine) -> None:
    current, old = AS_OF.replace(day=1), AS_OF.replace(month=AS_OF.month - 5, day=1)
    with engine.begin() as c:
        c.execute(
            db.monthly_snapshots.insert(),
            [
                {"format_id": 1, "barcode": B1, "month": current, "regular": 120, "discounted": 90},
                {
                    "format_id": 2,
                    "barcode": B1,
                    "month": current,
                    "regular": 160,
                    "discounted": None,
                },
                # A late per-format row for an already compacted month must not duplicate it.
                {"format_id": 1, "barcode": B1, "month": old, "regular": 999, "discounted": None},
            ],
        )
        c.execute(
            db.monthly_prices.insert().values(
                barcode=B1,
                month=old,
                min_regular=100,
                median_regular=110,
                max_regular=130,
                min_discounted=None,
                n_formats=3,
            )
        )
    query = (
        f'{{ product(barcode:"{B1}") {{ monthlyPrices(months:12) {{ month minRegularPara '
        "medianRegularPara maxRegularPara minDiscountedPara nFormats } } }"
    )
    response = client.post("/graphql", json={"query": query})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["product"]["monthlyPrices"] == [
        {
            "month": old.isoformat(),
            "minRegularPara": 100,
            "medianRegularPara": 110,
            "maxRegularPara": 130,
            "minDiscountedPara": None,
            "nFormats": 3,
        },
        {
            "month": current.isoformat(),
            "minRegularPara": 120,
            "medianRegularPara": 120,
            "maxRegularPara": 160,
            "minDiscountedPara": 90,
            "nFormats": 2,
        },
    ]
    short = client.post(
        "/graphql",
        json={"query": f'{{ product(barcode:"{B1}") {{ monthlyPrices(months:1) {{ month }} }} }}'},
    )
    assert short.json()["data"]["product"]["monthlyPrices"] == [{"month": current.isoformat()}]
    too_long = client.post(
        "/graphql",
        json={"query": f'{{ product(barcode:"{B1}") {{ monthlyPrices(months:25) {{ month }} }} }}'},
    )
    assert too_long.status_code == 422
    assert too_long.json()["detail"] == "Invalid GraphQL arguments: months"
