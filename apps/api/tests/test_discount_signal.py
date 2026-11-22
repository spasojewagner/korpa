import asyncio
import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from korpa_api.export_static import export
from korpa_ingest import db
from sqlalchemy.engine import Engine
from test_rest import AS_OF, B1, B2
from test_rest import client as client
from test_rest import engine as engine
from test_signals import changes, current


def discount(engine: Engine, **overrides: object) -> None:
    with engine.begin() as c:
        c.execute(
            db.prices_current.update()
            .where(
                db.prices_current.c.format_id == 1,
                db.prices_current.c.barcode == B1,
            )
            .values(
                **{
                    "discounted": 10000,
                    "disc_from": AS_OF - timedelta(days=2),
                    "disc_to": AS_OF,
                    **overrides,
                }
            )
        )


@pytest.mark.parametrize(
    ("rise", "discounted", "days_before", "expected"),
    [
        (11900, 10000, 1, False),
        (12000, 10000, 1, True),
        (12000, 9799, 1, False),
        (12000, 9800, 1, True),
        (12000, 9900, 1, True),
        (12000, 10000, 60, True),
        (12000, 10000, 61, False),
        (30000, 10000, 1, True),
        (30001, 10000, 1, False),
        (12000, 10000, 0, False),
        (12000, 10000, -1, False),
        (2000000000, 1600000000, 1, False),
    ],
)
def test_discount_rule_edges(
    client: TestClient,
    engine: Engine,
    rise: int,
    discounted: int,
    days_before: int,
    expected: bool,
) -> None:
    current(engine, [rise])
    changes(engine, [(90, 10000), (days_before + 2, rise)])
    discount(engine, discounted=discounted)
    response = client.get("/api/signals?type=discount_after_jump")
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == int(expected)
    if expected:
        assert items[0] == {
            "type": "discount_after_jump",
            "barcode": B1,
            "name": "Mleko",
            "retailer": "Povoljan",
            "format": "Market A",
            "date": (AS_OF - timedelta(days=days_before + 2)).isoformat(),
            "price_para": rise,
            "reference_para": 10000,
            "ratio": round(rise / 10000, 2),
            "old_regular_para": 10000,
            "new_regular_para": rise,
            "discounted_para": discounted,
            "rise_date": (AS_OF - timedelta(days=days_before + 2)).isoformat(),
            "disc_from": (AS_OF - timedelta(days=2)).isoformat(),
            "as_of": AS_OF.isoformat(),
        }


@pytest.mark.parametrize(
    "overrides",
    [
        {"discounted": None},
        {"disc_from": None},
        {"disc_to": None},
        {"disc_from": AS_OF + timedelta(days=1)},
        {"disc_to": AS_OF - timedelta(days=1)},
        {"list_date": AS_OF + timedelta(days=1)},
    ],
)
def test_discount_requires_active_dated_discount(
    client: TestClient,
    engine: Engine,
    overrides: dict[str, object],
) -> None:
    current(engine, [12000])
    changes(engine, [(90, 10000), (3, 12000)])
    discount(engine, **overrides)
    assert client.get("/api/signals?type=discount_after_jump").json()["items"] == []


def test_discount_consecutive_rows_partitions_and_zero_reference(
    client: TestClient,
    engine: Engine,
) -> None:
    current(engine, [14400])
    discount(engine)
    changes(engine, [(90, 10000), (10, 12000), (3, 14400)])
    with engine.begin() as c:
        c.execute(
            db.price_changes.insert(),
            [
                {
                    "format_id": 2,
                    "barcode": B1,
                    "changed_on": AS_OF - timedelta(days=4),
                    "regular": 50000,
                },
                {
                    "format_id": 1,
                    "barcode": B2,
                    "changed_on": AS_OF - timedelta(days=4),
                    "regular": 50000,
                },
            ],
        )
    items = client.get("/api/signals?type=discount_after_jump").json()["items"]
    assert [item["old_regular_para"] for item in items] == [10000]
    changes(engine, [(90, 10000), (10, 0), (3, 12000)])
    assert client.get("/api/signals?type=discount_after_jump").json()["items"] == []


def test_discount_inclusive_dates_large_money_and_export(
    client: TestClient,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    current(engine, [2000000000])
    changes(engine, [(90, 1600000000), (1, 2000000000)])
    discount(engine, discounted=1600000000, disc_from=AS_OF, disc_to=AS_OF)
    items = client.get("/api/signals?type=discount_after_jump").json()["items"]
    assert len(items) == 1 and items[0]["ratio"] == 1.25
    assert items[0] in client.get("/api/signals").json()["items"]
    monkeypatch.setattr("korpa_api.export_static.belgrade_today", lambda: AS_OF)
    asyncio.run(export(tmp_path))
    assert json.loads((tmp_path / "signals.json").read_text("utf-8")) == (
        client.get("/api/signals?limit=200").json()
    )


def test_name_variants_exact_names_share_and_export(
    client: TestClient,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with engine.begin() as c:
        c.execute(
            db.product_names.insert(),
            [
                {"barcode": B1, "retailer_id": 1, "raw_name": "MLEKO"},
                {"barcode": B1, "retailer_id": 2, "raw_name": "Mleko"},
                {"barcode": B2, "retailer_id": 1, "raw_name": "Čokolada"},
                {"barcode": B2, "retailer_id": 2, "raw_name": "Čokolada"},
            ],
        )
    quality = client.get("/api/quality").json()
    assert quality["name_variants"] == {
        "barcodes": 1,
        "share_of_products": 1 / 3,
        "examples": [
            {
                "barcode": B1,
                "names": [
                    {"retailer": "Povoljan", "name": "MLEKO"},
                    {"retailer": "Delimičan", "name": "Mleko"},
                ],
            }
        ],
    }
    assert quality["retailers"][0]["status"] == "partial"
    monkeypatch.setattr("korpa_api.export_static.belgrade_today", lambda: AS_OF)
    asyncio.run(export(tmp_path))
    assert json.loads((tmp_path / "quality.json").read_text("utf-8")) == quality


def test_name_variants_empty_and_capped_deterministically(
    client: TestClient,
    engine: Engine,
) -> None:
    assert client.get("/api/quality").json()["name_variants"] == {
        "barcodes": 0,
        "share_of_products": 0,
        "examples": [],
    }
    with engine.begin() as c:
        c.execute(
            db.retailers.insert(),
            {
                "id": 4,
                "name": "Četvrti",
                "slug": "r4",
                "dataset_id": "d4",
                "resource_url": "https://example.org/4.csv",
            },
        )
        c.execute(
            db.products.insert(),
            [
                {
                    "barcode": f"{i:013d}",
                    "name": str(i),
                    "brand": "",
                    "unit": "kom",
                    "category_code": 1,
                }
                for i in range(1000, 1006)
            ],
        )
        c.execute(
            db.product_names.insert(),
            [
                {"barcode": f"{i:013d}", "retailer_id": r, "raw_name": f"Naziv {r}"}
                for i in range(1000, 1006)
                for r in range(1, 5)
            ],
        )
    data = client.get("/api/quality").json()["name_variants"]
    assert data["barcodes"] == 6 and data["share_of_products"] == 6 / 9
    assert [e["barcode"] for e in data["examples"]] == [f"{i:013d}" for i in range(1000, 1005)]
    assert all(len(e["names"]) == 3 for e in data["examples"])
    assert client.get("/api/quality").json()["name_variants"] == data
    with engine.begin() as c:
        for table in reversed(db.metadata.sorted_tables):
            c.execute(table.delete())
    assert client.get("/api/quality").json()["name_variants"] == {
        "barcodes": 0,
        "share_of_products": 0,
        "examples": [],
    }
