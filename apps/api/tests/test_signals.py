import asyncio
import json
from datetime import timedelta
from pathlib import Path
from statistics import median_low

import pytest
from fastapi.testclient import TestClient
from korpa_api.export_static import export
from korpa_ingest import db
from sqlalchemy.engine import Engine
from test_rest import AS_OF, B1, B2
from test_rest import client as client
from test_rest import engine as engine


def current(engine: Engine, prices: list[int]) -> None:
    with engine.begin() as c:
        c.execute(db.prices_current.delete())
        c.execute(db.price_changes.delete())
        for f in range(5, len(prices) + 1):
            c.execute(db.retail_formats.insert().values(id=f, retailer_id=1, name=f"Format {f}"))
        c.execute(
            db.prices_current.insert(),
            [
                {
                    "format_id": i,
                    "barcode": B1,
                    "regular": price,
                    "unit_price": price,
                    "vat": 20,
                    "list_date": AS_OF,
                }
                for i, price in enumerate(prices, 1)
            ],
        )


def changes(engine: Engine, observations: list[tuple[int, int]]) -> None:
    with engine.begin() as c:
        c.execute(db.price_changes.delete())
        c.execute(
            db.price_changes.insert(),
            [
                {
                    "format_id": 1,
                    "barcode": B1,
                    "changed_on": AS_OF - timedelta(days=days),
                    "regular": price,
                    "discounted": 0,
                }
                for days, price in observations
            ],
        )


@pytest.mark.parametrize(("price", "expected"), [(12490, False), (12500, True)])
def test_jump_exact_threshold(
    client: TestClient, engine: Engine, price: int, expected: bool
) -> None:
    changes(engine, [(45, 10000), (1, price)])
    result = client.get("/api/signals", params={"type": "jump"})
    assert result.status_code == 200, result.text
    items = result.json()["items"]
    assert len(items) == int(expected)
    if expected:
        assert items[0] == {
            "type": "jump",
            "barcode": B1,
            "name": "Mleko",
            "retailer": "Povoljan",
            "format": "Market A",
            "date": (AS_OF - timedelta(days=1)).isoformat(),
            "price_para": 12500,
            "reference_para": 10000,
            "ratio": 1.25,
        }


@pytest.mark.parametrize(("days", "expected"), [(30, True), (31, False), (0, True), (-1, False)])
def test_jump_window_includes_boundary_and_ignores_future(
    client: TestClient, engine: Engine, days: int, expected: bool
) -> None:
    changes(engine, [(60, 10000), (days, 12500)])
    assert len(client.get("/api/signals?type=jump").json()["items"]) == int(expected)


def test_jump_uses_consecutive_rows_even_when_predecessor_is_outside_window(
    client: TestClient, engine: Engine
) -> None:
    changes(engine, [(60, 10000), (40, 20000), (1, 24980)])
    assert client.get("/api/signals?type=jump").json()["items"] == []
    changes(engine, [(60, 10000), (40, 20000), (1, 25000)])
    item = client.get("/api/signals?type=jump").json()["items"][0]
    assert item["reference_para"] == 20000 and item["ratio"] == 1.25


def test_zero_reference_does_not_fall_back_to_an_older_price(
    client: TestClient, engine: Engine
) -> None:
    changes(engine, [(40, 10000), (20, 0), (1, 20000)])
    assert client.get("/api/signals?type=jump").json()["items"] == []


def test_jump_emits_each_recent_increase_newest_first(client: TestClient, engine: Engine) -> None:
    changes(engine, [(40, 10000), (2, 12500), (1, 15625)])
    items = client.get("/api/signals?type=jump").json()["items"]
    assert [p["price_para"] for p in items] == [15625, 12500]
    assert [p["reference_para"] for p in items] == [12500, 10000]


@pytest.mark.parametrize(("price", "expected"), [(14900, False), (15000, True)])
def test_outlier_exact_threshold(
    client: TestClient, engine: Engine, price: int, expected: bool
) -> None:
    current(engine, [price, 10000, 10000, 10000])
    items = client.get("/api/signals?type=outlier").json()["items"]
    assert len(items) == int(expected)
    if expected:
        assert items[0]["price_para"] == 15000
        assert items[0]["reference_para"] == 10000
        assert items[0]["ratio"] == 1.5
        assert items[0]["date"] == AS_OF.isoformat()


def test_outlier_needs_three_other_formats(client: TestClient, engine: Engine) -> None:
    current(engine, [30000, 10000, 10000])
    assert client.get("/api/signals?type=outlier").json()["items"] == []


@pytest.mark.parametrize(
    "prices",
    [
        [30000, 10000, 10000, 10000, 12000],
        [10000, 20000, 30000, 40000],
        [10000, 10000, 15000, 15000, 15000],
        [10000, 12000, 13000, 14000, 15000, 30000],
        [0, 0, 0, 10000],
    ],
)
def test_other_format_median_excludes_self_and_handles_ties_and_even_counts(
    client: TestClient, engine: Engine, prices: list[int]
) -> None:
    current(engine, prices)
    items = client.get("/api/signals?type=outlier").json()["items"]
    expected = sorted(
        (price, median_low(prices[:i] + prices[i + 1 :]))
        for i, price in enumerate(prices)
        if median_low(prices[:i] + prices[i + 1 :]) > 0
        and price * 2 >= median_low(prices[:i] + prices[i + 1 :]) * 3
    )
    assert sorted((p["price_para"], p["reference_para"]) for p in items) == expected
    for item in items:
        assert item["ratio"] == round(item["price_para"] / item["reference_para"], 2)


@pytest.mark.parametrize(
    ("start", "end", "expected"), [(0, 0, False), (-2, -1, True), (1, 2, True)]
)
def test_effective_price_respects_inclusive_discount_dates(
    client: TestClient, engine: Engine, start: int, end: int, expected: bool
) -> None:
    current(engine, [20000, 10000, 10000, 10000])
    with engine.begin() as c:
        c.execute(
            db.prices_current.update()
            .where(db.prices_current.c.format_id == 1)
            .values(
                discounted=14000,
                disc_from=AS_OF + timedelta(days=start),
                disc_to=AS_OF + timedelta(days=end),
            )
        )
    items = client.get("/api/signals?type=outlier").json()["items"]
    assert len(items) == int(expected)
    if expected:
        assert items[0]["price_para"] == 20000


def test_other_formats_use_current_effective_prices_and_future_lists_do_not_count(
    client: TestClient, engine: Engine
) -> None:
    current(engine, [20000, 20000, 20000, 20000])
    with engine.begin() as c:
        c.execute(
            db.prices_current.update()
            .where(db.prices_current.c.format_id != 1)
            .values(discounted=10000, disc_from=AS_OF, disc_to=AS_OF)
        )
    assert client.get("/api/signals?type=outlier").json()["items"][0]["reference_para"] == 10000
    with engine.begin() as c:
        c.execute(
            db.prices_current.update()
            .where(db.prices_current.c.format_id == 4)
            .values(list_date=AS_OF + timedelta(days=1))
        )
    assert client.get("/api/signals?type=outlier").json()["items"] == []


def test_both_types_filter_and_deterministic_ties(client: TestClient, engine: Engine) -> None:
    current(engine, [20000, 10000, 10000, 10000])
    changes(engine, [(40, 16000), (0, 20000)])
    items = client.get("/api/signals").json()["items"]
    assert [p["type"] for p in items] == ["jump", "outlier"]
    assert len(client.get("/api/signals?type=jump").json()["items"]) == 1
    assert len(client.get("/api/signals?type=outlier").json()["items"]) == 1
    assert client.get("/api/signals?limit=1").json()["items"] == items[:1]


@pytest.mark.parametrize("query", ["type=unknown", "limit=0", "limit=201", "limit=no", "q=extra"])
def test_invalid_signal_parameters_are_problem_json(client: TestClient, query: str) -> None:
    response = client.get("/api/signals?" + query)
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"


def many_jumps(engine: Engine) -> None:
    with engine.begin() as c:
        c.execute(db.price_changes.delete())
        c.execute(
            db.products.insert(),
            [
                {
                    "barcode": f"{i:013d}",
                    "name": f"Proizvod {i}",
                    "brand": "",
                    "unit": "kom",
                    "category_code": 1,
                }
                for i in range(1000, 1205)
            ],
        )
        c.execute(
            db.price_changes.insert(),
            [
                {
                    "barcode": f"{i:013d}",
                    "format_id": 1,
                    "changed_on": AS_OF - timedelta(days=days),
                    "regular": price,
                }
                for i in range(1000, 1205)
                for days, price in ((40, 10000), (0, 12500))
            ],
        )


def test_limits_and_static_equals_rest(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    many_jumps(engine)
    assert len(client.get("/api/signals").json()["items"]) == 100
    expected = client.get("/api/signals?limit=200").json()
    assert len(expected["items"]) == 200
    assert [p["barcode"] for p in expected["items"]] == sorted(
        p["barcode"] for p in expected["items"]
    )
    monkeypatch.setattr("korpa_api.export_static.belgrade_today", lambda: AS_OF)
    asyncio.run(export(tmp_path))
    assert json.loads((tmp_path / "signals.json").read_text("utf-8")) == expected


def test_signals_database_failure_is_problem_json(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail(*args: object, **kwargs: object) -> None:
        raise ConnectionRefusedError("private")

    monkeypatch.setattr("korpa_api.analytics.signals", fail)
    response = client.get("/api/signals")
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert "private" not in response.text


def test_jump_partitions_by_both_format_and_product(client: TestClient, engine: Engine) -> None:
    changes(engine, [(2, 10000), (0, 12500)])
    with engine.begin() as c:
        c.execute(
            db.price_changes.insert(),
            [
                {
                    "format_id": 2,
                    "barcode": B1,
                    "changed_on": AS_OF - timedelta(days=1),
                    "regular": 20000,
                },
                {
                    "format_id": 1,
                    "barcode": B2,
                    "changed_on": AS_OF - timedelta(days=1),
                    "regular": 30000,
                },
            ],
        )
    items = client.get("/api/signals?type=jump").json()["items"]
    assert len(items) == 1
    assert items[0]["barcode"] == B1 and items[0]["format"] == "Market A"
    assert items[0]["reference_para"] == 10000


def test_threshold_multiplication_does_not_overflow_integer_money(
    client: TestClient, engine: Engine
) -> None:
    current(engine, [2000000000, 1000000000, 1000000000, 1000000000])
    changes(engine, [(2, 1600000000), (0, 2000000000)])
    items = client.get("/api/signals").json()["items"]
    assert [p["type"] for p in items] == ["jump", "outlier"]
    assert [p["ratio"] for p in items] == [1.25, 2.0]
