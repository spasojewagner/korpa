import asyncio
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from importlib.resources import files
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from korpa_api.export_static import export
from korpa_api.main import app
from korpa_api.pricing import effective_price
from korpa_api.translit import normalize, normalize_query, transliterate
from korpa_ingest import db
from sqlalchemy.engine import Engine

AS_OF = date(2026, 11, 21)
B1, B2, B3 = "0000000000001", "0000000000002", "0000000000003"


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL API integration tests")
    assert sa.engine.make_url(url).database in {"korpa_test", "korpa_api_test"}
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": url},
        check=True,
    )
    instance = sa.create_engine(url)
    yield instance
    instance.dispose()


@pytest.fixture()
def client(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    with engine.begin() as c:
        for table in reversed(db.metadata.sorted_tables):
            c.execute(table.delete())
        c.execute(
            db.categories.insert(), [{"code": 1, "name": "Hrana"}, {"code": 2, "name": "Piće"}]
        )
        c.execute(
            db.retailers.insert(),
            [
                {
                    "id": i,
                    "name": name,
                    "slug": f"r{i}",
                    "dataset_id": f"d{i}",
                    "resource_url": f"https://example.org/{i}.csv",
                }
                for i, name in enumerate(["Povoljan", "Delimičan", "Prazan"], 1)
            ],
        )
        c.execute(
            db.retail_formats.insert(),
            [
                {"id": 1, "retailer_id": 1, "name": "Market A"},
                {"id": 2, "retailer_id": 1, "name": "Market B"},
                {"id": 3, "retailer_id": 2, "name": "Delimični market"},
                {"id": 4, "retailer_id": 3, "name": "Prazni market"},
            ],
        )
        c.execute(
            db.products.insert(),
            [
                {
                    "barcode": B1,
                    "name": "Mleko",
                    "brand": "Domaće",
                    "unit": "l",
                    "category_code": 1,
                },
                {
                    "barcode": B2,
                    "name": "Čokolada",
                    "brand": "Slatko",
                    "unit": "g",
                    "category_code": 1,
                },
                {"barcode": B3, "name": "Đus", "brand": "Voće", "unit": "l", "category_code": 2},
            ],
        )
        c.execute(
            db.prices_current.insert(),
            [
                {
                    "format_id": f,
                    "barcode": barcode,
                    "regular": price,
                    "discounted": discount,
                    "disc_from": AS_OF if discount is not None else None,
                    "disc_to": AS_OF if discount is not None else None,
                    "unit_price": price,
                    "vat": 20,
                    "list_date": AS_OF - timedelta(days=f),
                }
                for f, barcode, price, discount in [
                    (1, B1, 100, 80),
                    (1, B2, 200, None),
                    (2, B1, 105, None),
                    (2, B2, 190, None),
                    (3, B1, 10, None),
                    (1, B3, 300, None),
                ]
            ],
        )
        c.execute(
            db.ingest_runs.insert(),
            [
                {
                    "retailer_id": 1,
                    "started_at": datetime.now(UTC),
                    "finished_at": datetime.now(UTC),
                    "http_status": 200,
                    "rows_total": 10,
                    "rows_valid": 9,
                    "errors_json": {
                        "errors": {"unit": 1},
                        "deviations": {"unit_case": 2},
                        "profile": "compat-2026-11",
                    },
                },
            ],
        )
    monkeypatch.setenv("DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr("korpa_api.routes.belgrade_today", lambda: AS_OF)
    with TestClient(app) as instance:
        yield instance


@pytest.mark.parametrize(
    ("query", "name"),
    [
        ("mleko", "Mleko"),
        ("MLEKO", "Mleko"),
        ("cokolada", "Čokolada"),
        ("čokolada", "Čokolada"),
        ("шоколада", "Čokolada"),
        ("djus", "Đus"),
        ("đus", "Đus"),
        ("cokolda", "Čokolada"),
        (B2, "Čokolada"),
    ],
)
def test_required_search_cases(client: TestClient, query: str, name: str) -> None:
    response = client.get("/api/search", params={"q": query})
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["name"] == name
    assert response.json()["as_of"] == AS_OF.isoformat()
    assert response.headers["cache-control"] == "public, max-age=300"


def test_search_aggregates_and_filters(client: TestClient) -> None:
    data = client.get("/api/search", params={"q": "mleko"}).json()
    item = data["items"][0]
    assert (item["min_effective_para"], item["max_effective_para"], item["n_formats"]) == (
        10,
        105,
        3,
    )
    assert item["any_discount"] is True
    assert item["list_date"] == (AS_OF - timedelta(days=1)).isoformat()
    assert client.get("/api/search", params={"q": "mleko", "category": 2}).json()["total"] == 0
    assert client.get("/api/search", params={"q": "mleko", "offset": 1}).json() == {
        "items": [],
        "total": 1,
        "as_of": AS_OF.isoformat(),
    }


def test_category_browsing_orders_by_formats_then_name_and_barcode(
    client: TestClient,
    engine: Engine,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            db.products.insert(),
            [
                {"barcode": code, "name": name, "brand": "", "unit": "l", "category_code": 1}
                for code, name in [
                    ("0000000000004", "Abc"),
                    ("0000000000005", "Abc"),
                    ("0000000000006", "Bez cene"),
                ]
            ],
        )
        connection.execute(
            db.prices_current.insert(),
            [
                {
                    "barcode": code,
                    "format_id": f,
                    "regular": 0,
                    "unit_price": 0,
                    "vat": 20,
                    "list_date": AS_OF,
                }
                for code in ("0000000000004", "0000000000005")
                for f in (1, 2)
            ],
        )
    response = client.get("/api/search", params={"category": 1})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 4
    assert [item["barcode"] for item in data["items"]] == [
        B1,
        "0000000000004",
        "0000000000005",
        B2,
    ]
    assert [item["n_formats"] for item in data["items"]] == [3, 2, 2, 2]
    assert data["items"][1]["min_effective_para"] == 0
    assert data["items"][0]["min_effective_para"] == 10
    assert data["items"][0]["any_discount"] is True
    assert data["items"][0]["list_date"] == (AS_OF - timedelta(days=1)).isoformat()
    assert data["as_of"] == AS_OF.isoformat()
    assert response.headers["cache-control"] == "public, max-age=300"
    page = client.get("/api/search", params={"category": 1, "limit": 2, "offset": 1}).json()
    assert page["items"] == data["items"][1:3]
    assert page["total"] == 4
    for category in (3, 25):
        assert client.get("/api/search", params={"category": category}).json() == {
            "items": [],
            "total": 0,
            "as_of": AS_OF.isoformat(),
        }


def test_category_browsing_excludes_withdrawn_products(
    client: TestClient,
    engine: Engine,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            db.monthly_snapshots.insert().values(
                format_id=1,
                barcode=B1,
                month=AS_OF.replace(day=1),
                regular=100,
            )
        )
        connection.execute(db.prices_current.delete().where(db.prices_current.c.barcode == B1))
    data = client.get("/api/search", params={"category": 1}).json()
    assert data["total"] == 1
    assert [item["barcode"] for item in data["items"]] == [B2]


def test_search_openapi_documents_optional_text_and_category_requirement() -> None:
    operation = app.openapi()["paths"]["/api/search"]["get"]
    params = {p["name"]: p for p in operation["parameters"]}
    assert params["q"]["required"] is False
    assert params["category"]["required"] is False
    assert "At least one of q or category is required" in operation["description"]


@pytest.mark.parametrize("query", ["mleko", "0000000000004"])
def test_search_excludes_products_without_current_prices(
    client: TestClient,
    engine: Engine,
    query: str,
) -> None:
    unpriced_barcode = "0000000000004"
    with engine.begin() as connection:
        connection.execute(
            db.products.insert().values(
                barcode=unpriced_barcode,
                name="Mleko bez cene",
                brand="Domaće",
                unit="l",
                category_code=1,
            )
        )
    response = client.get("/api/search", params={"q": query})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == (1 if query == "mleko" else 0)
    assert unpriced_barcode not in [item["barcode"] for item in data["items"]]
    for item in data["items"]:
        assert item["n_formats"] >= 1
        assert item["min_effective_para"] is not None
        assert item["max_effective_para"] is not None
        assert item["list_date"] is not None


def test_withdrawn_product_history_does_not_keep_it_in_price_search(
    client: TestClient,
    engine: Engine,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            db.monthly_snapshots.insert().values(
                format_id=1,
                barcode=B1,
                month=AS_OF.replace(day=1),
                regular=100,
            )
        )
        connection.execute(db.prices_current.delete().where(db.prices_current.c.barcode == B1))
    for query in ("mleko", B1):
        response = client.get("/api/search", params={"q": query})
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0, "as_of": AS_OF.isoformat()}


def test_search_openapi_requires_price_and_source_date() -> None:
    properties = app.openapi()["components"]["schemas"]["SearchItem"]["properties"]
    assert properties["min_effective_para"]["type"] == "integer"
    assert properties["max_effective_para"]["type"] == "integer"
    assert properties["list_date"]["type"] == "string"
    assert properties["list_date"]["format"] == "date"


@pytest.mark.parametrize("query", ["unfindableword", "0000000000099", "'; DROP TABLE products;--"])
def test_unknown_query_returns_empty_200(client: TestClient, query: str) -> None:
    response = client.get("/api/search", params={"q": query})
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_basket_ranks_complete_before_partial_and_merges_duplicates(client: TestClient) -> None:
    response = client.post(
        "/api/basket",
        json={
            "items": [
                {"barcode": B1, "qty": 2},
                {"barcode": B1, "qty": 3},
                {"barcode": B2, "qty": 1},
            ]
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    formats = sorted(
        [f for r in result["retailers"] for f in r["formats"]], key=lambda f: f["rank"]
    )
    assert [f["id"] for f in formats] == [1, 2, 3]
    assert [f["total_para"] for f in formats] == [600, 715, 50]
    assert [f["complete"] for f in formats] == [True, True, False]
    assert formats[2]["missing_barcodes"] == [B2]
    assert result["as_of"] == AS_OF.isoformat()


def test_basket_partial_ranking_prefers_more_found_over_cheaper_total(client: TestClient) -> None:
    formats = sorted(
        [
            f
            for r in client.post(
                "/api/basket",
                json={
                    "items": [
                        {"barcode": B1, "qty": 1},
                        {"barcode": B2, "qty": 1},
                        {"barcode": "0000000000099", "qty": 1},
                    ]
                },
            ).json()["retailers"]
            for f in r["formats"]
        ],
        key=lambda f: f["rank"],
    )
    assert [f["id"] for f in formats] == [1, 2, 3]
    assert not any(f["complete"] for f in formats)


def test_basket_omits_formats_and_retailers_with_no_requested_products(client: TestClient) -> None:
    response = client.post("/api/basket", json={"items": [{"barcode": B3, "qty": 1}]})
    assert response.status_code == 200
    retailers = response.json()["retailers"]
    assert [retailer["id"] for retailer in retailers] == [1]
    assert [row["id"] for row in retailers[0]["formats"]] == [1]
    assert retailers[0]["formats"][0]["found_barcodes"] == [B3]


def test_basket_returns_no_formats_when_every_barcode_is_missing(client: TestClient) -> None:
    response = client.post("/api/basket", json={"items": [{"barcode": "0000000000099", "qty": 1}]})
    assert response.status_code == 200
    assert response.json() == {"retailers": [], "as_of": AS_OF.isoformat()}


def test_basket_keeps_a_found_product_with_a_genuine_zero_price(
    client: TestClient,
    engine: Engine,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            db.prices_current.update()
            .where(
                db.prices_current.c.barcode == B3,
            )
            .values(regular=0, unit_price=0)
        )
    response = client.post("/api/basket", json={"items": [{"barcode": B3, "qty": 1}]})
    assert response.status_code == 200
    formats = response.json()["retailers"][0]["formats"]
    assert len(formats) == 1
    assert formats[0]["found_barcodes"] == [B3]
    assert formats[0]["total_para"] == 0
    assert formats[0]["complete"] is True


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"category": 0},
        {"category": 26},
        {"category": 1, "q": ""},
        {"category": 1, "q": "a"},
        {"category": 1, "q": "   "},
        {"category": 1, "q": "a" * 101},
        {"category": 1, "limit": 0},
        {"category": 1, "limit": 51},
        {"category": 1, "offset": -1},
        {"category": 1, "offset": 1001},
        {"category": 1, "unexpected": "value"},
        {"q": "a"},
        {"q": " " * 3},
        {"q": "a" * 101},
        {"q": "mleko", "limit": 51},
        {"q": "mleko", "limit": 0},
        {"q": "mleko", "offset": 1001},
        {"q": "mleko", "offset": -1},
        {"q": "mleko", "category": 26},
    ],
)
def test_search_caps_and_problem_json(client: TestClient, params: dict[str, object]) -> None:
    response = client.get("/api/search", params=params)
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "about:blank"
    assert response.json()["status"] == 422
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "body",
    [
        {"items": []},
        {"items": [{"barcode": B1, "qty": 0}]},
        {"items": [{"barcode": B1, "qty": 100}]},
        {"items": [{"barcode": "123", "qty": 1}]},
        {"items": [{"barcode": B1, "qty": True}]},
        {"items": [{"barcode": B1, "qty": 99}, {"barcode": B1, "qty": 1}]},
        {"items": [{"barcode": B1, "qty": 1}] * 51},
    ],
)
def test_basket_caps(client: TestClient, body: dict[str, object]) -> None:
    response = client.post("/api/basket", json=body)
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


def test_categories_quality_and_read_only_methods(client: TestClient) -> None:
    assert client.get("/api/categories").json() == [
        {"code": 1, "name": "Hrana", "n_products": 2},
        {"code": 2, "name": "Piće", "n_products": 1},
    ]
    quality = client.get("/api/quality").json()["retailers"]
    assert quality[0]["status"] == "partial"
    assert quality[0]["errors"] == {"unit": 1}
    assert quality[0]["days_since_list_date"] == 1
    assert quality[1]["status"] == "never"
    assert client.put("/api/categories").status_code == 405
    assert client.get("/not-found").headers["content-type"] == "application/problem+json"
    cors = client.options(
        "/api/basket",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert cors.status_code == 200


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
def test_effective_price_window_edges(
    engine: Engine,
    start: date | None,
    end: date | None,
    discount: int | None,
    expected: int,
) -> None:
    with engine.connect() as c:
        result = c.scalar(
            sa.select(
                effective_price(
                    sa.literal(100),
                    sa.literal(discount, sa.Integer),
                    sa.literal(start, sa.Date),
                    sa.literal(end, sa.Date),
                    AS_OF,
                )
            )
        )
        assert result == expected


def test_python_and_sql_normalization_match(engine: Engine) -> None:
    words = [
        "MLEKO",
        "Čokolada",
        "Đus",
        "DŽEM",
        "Voće",
        "Ćevapčići",
        "Žućko",
        "ĐORĐE",
        "čćšžđ",
        "Straße",
        "Œuf",
        "Łódź",
        "Æble",
        "Øst",
        "½",
        "café",
    ]
    with engine.connect() as c:
        for word in words:
            assert c.scalar(sa.text("SELECT korpa_norm(:word)"), {"word": word}) == normalize(word)
    assert transliterate("Љ Њ Џ Ђ љ њ џ ђ") == "Lj Nj Dž Đ lj nj dž đ"
    assert normalize_query("Чоколада") == "cokolada"


def test_python_twin_matches_the_installed_dictionary_corpus(engine: Engine) -> None:
    mappings = json.loads(
        files("korpa_api").joinpath("data/unaccent16.json").read_text(encoding="utf-8")
    )
    keys = list(mappings)
    with engine.connect() as c:
        rows = c.execute(
            sa.text("SELECT k, korpa_norm(k) FROM unnest(CAST(:keys AS text[])) k"), {"keys": keys}
        )
        assert all(normalize(key) == value for key, value in rows)


def test_search_vector_tracks_ingest_insert_and_rename(client: TestClient, engine: Engine) -> None:
    with engine.begin() as c:
        c.execute(
            db.products.update()
            .where(db.products.c.barcode == B2)
            .values(
                name="Čokoladica",
                search_tsv=sa.func.to_tsvector("simple", "incorrect"),
            )
        )
        assert c.scalar(
            sa.select(db.products.c.search_norm).where(db.products.c.barcode == B2)
        ) == ("cokoladica slatko")
    assert client.get("/api/search", params={"q": "cokoladica"}).json()["items"][0]["barcode"] == B2


def test_unexpected_failures_are_problem_json_without_internal_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(*args: object, **kwargs: object) -> list[object]:
        raise RuntimeError("private internal diagnostic")

    monkeypatch.setattr("korpa_api.repository.categories", fail)
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.get("/api/categories")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert "private" not in response.text


def test_raw_connection_failures_are_problem_json(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(*args: object, **kwargs: object) -> list[object]:
        raise ConnectionRefusedError("private connection information")

    monkeypatch.setattr("korpa_api.repository.categories", fail)
    response = client.get("/api/categories")
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert "private" not in response.text


def test_openapi_documents_problem_media_and_schema() -> None:
    schema = app.openapi()
    for path, method in [
        ("/api/search", "get"),
        ("/api/basket", "post"),
        ("/api/categories", "get"),
        ("/api/quality", "get"),
    ]:
        responses = schema["paths"][path][method]["responses"]
        for status in ("422", "500", "503"):
            content = responses[status]["content"]
            assert set(content) == {"application/problem+json"}
            assert (
                content["application/problem+json"]["schema"]["properties"]["status"]["type"]
                == "integer"
            )


def test_static_export_matches_rest_responses(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr("korpa_api.export_static.belgrade_today", lambda: AS_OF)
    asyncio.run(export(tmp_path))
    for name, path in (("categories.json", "/api/categories"), ("quality.json", "/api/quality")):
        assert json.loads((tmp_path / name).read_text("utf-8")) == client.get(path).json()


def test_search_prefers_names_that_start_with_the_query(client: TestClient, engine: Engine) -> None:
    milk, substitute = "0000000000101", "0000000000102"
    with engine.begin() as c:
        c.execute(
            db.products.insert(),
            [
                {
                    "barcode": milk,
                    "name": "Mleko trajno 2,8% mlečne masti 1 l",
                    "brand": "Imlek",
                    "unit": "l",
                    "category_code": 1,
                },
                {
                    "barcode": substitute,
                    "name": "Zamena za mleko",
                    "brand": "",
                    "unit": "kg",
                    "category_code": 1,
                },
            ],
        )
        c.execute(
            db.prices_current.insert(),
            [
                {
                    "format_id": f,
                    "barcode": code,
                    "regular": 15000,
                    "unit_price": 15000,
                    "vat": 20,
                    "list_date": AS_OF,
                }
                for code, formats in ((milk, (1, 2, 3)), (substitute, (1,)))
                for f in formats
            ],
        )
    items = client.get("/api/search", params={"q": "mleko"}).json()["items"]
    order = [item["barcode"] for item in items]
    assert order.index(milk) < order.index(substitute)
