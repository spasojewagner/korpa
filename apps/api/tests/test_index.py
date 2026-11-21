import asyncio
import json
from datetime import date
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from korpa_api.analytics import refresh_index
from korpa_api.export_static import export
from korpa_ingest import db
from korpa_ingest.store import compact_monthly
from sqlalchemy.engine import Engine
from test_rest import client as client
from test_rest import engine as engine

BASE, NEXT, CURRENT = date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)
AS_OF = date(2026, 10, 15)


def seed(
    engine: Engine, n: int = 30, extra: list[tuple[int | None, int | None]] | None = None
) -> None:
    with engine.begin() as c:
        for table in (
            db.index_monthly,
            db.prices_current,
            db.monthly_snapshots,
            db.monthly_prices,
            db.products,
        ):
            c.execute(table.delete())
        for i, (base, target) in enumerate([(300, 330)] * n + (extra or []), 1):
            barcode = f"{i:013d}"
            c.execute(
                db.products.insert().values(
                    barcode=barcode, name=f"Proizvod {i}", brand="", unit="kom", category_code=1
                )
            )
            for month, price in ((BASE, base), (NEXT, target)):
                if price is not None:
                    c.execute(
                        db.monthly_snapshots.insert(),
                        [
                            {
                                "format_id": f,
                                "barcode": barcode,
                                "month": month,
                                "regular": price * factor,
                                "discounted": 0,
                            }
                            for f, factor in ((1, 0), (2, 1), (3, 3))
                        ],
                    )
            if target is not None:
                c.execute(
                    db.prices_current.insert(),
                    [
                        {
                            "format_id": f,
                            "barcode": barcode,
                            "regular": target * factor,
                            "discounted": 0,
                            "unit_price": target,
                            "vat": 20,
                            "list_date": AS_OF,
                        }
                        for f, factor in ((1, 0), (2, 1), (3, 3))
                    ],
                )


def read(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr("korpa_api.routes.belgrade_today", lambda: AS_OF)
    response = client.get("/api/index")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "public, max-age=300"
    return response.json()


def test_base_rise_medians_overall_provisional_and_idempotent_cache(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(engine)
    refresh_index(engine, AS_OF)
    refresh_index(engine, AS_OF)
    result = read(client, monkeypatch)
    assert result["as_of"] == AS_OF.isoformat()
    assert result["base_month"] == BASE.isoformat()
    assert [c["code"] for c in result["categories"]] == [0, 1, 2]
    assert result["categories"][0]["name"] == "Sve kategorije"
    points = result["categories"][0]["points"]
    assert points == [
        {
            "month": BASE.isoformat(),
            "value": 100.0,
            "n_products": 30,
            "n_excluded": 0,
            "provisional": False,
        },
        {
            "month": NEXT.isoformat(),
            "value": 110.0,
            "n_products": 30,
            "n_excluded": 0,
            "provisional": False,
        },
        {
            "month": CURRENT.isoformat(),
            "value": 110.0,
            "n_products": 30,
            "n_excluded": 0,
            "provisional": True,
        },
    ]
    assert result["categories"][1]["points"] == points
    assert all(
        p["value"] is None and p["n_products"] == 0 for p in result["categories"][2]["points"]
    )
    with engine.connect() as c:
        assert c.scalar(sa.select(sa.func.count()).select_from(db.index_monthly)) == 6
        assert c.scalar(sa.select(sa.func.max(db.index_monthly.c.month))) == NEXT
    # Current prices change on read, without changing any persisted month.
    with engine.begin() as c:
        c.execute(db.prices_current.update().values(regular=360))
    assert read(client, monkeypatch)["categories"][0]["points"][-1]["value"] == 120.0


@pytest.mark.parametrize("n", [29, 30])
def test_exclusion_counts_and_threshold_after_exclusions(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch, n: int
) -> None:
    # Both inclusive limits enter the mean and cancel geometrically. Missing rows on
    # either side, 0/0, zero numerator/denominator and ratios just outside are excluded.
    seed(
        engine,
        n - 2,
        [
            (300, 100),
            (300, 900),
            (300, 99),
            (300, 901),
            (0, 330),
            (300, 0),
            (0, 0),
            (None, 330),
            (300, None),
        ],
    )
    refresh_index(engine, AS_OF)
    result = read(client, monkeypatch)
    expected = round(100 * 1.1 ** ((n - 2) / n), 4) if n == 30 else None
    for category in result["categories"][:2]:
        for point in category["points"][1:]:
            assert point["n_products"] == n
            assert point["n_excluded"] == 7
            assert point["value"] == expected
        # Two zero-base products and one missing-base newcomer are excluded even at base.
        assert category["points"][0]["n_excluded"] == 2


def test_compacted_and_live_history_and_late_rows_refresh_cache(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(engine)
    assert compact_monthly(engine, date(2026, 11, 1)) == 90
    refresh_index(engine, AS_OF)
    assert read(client, monkeypatch)["categories"][0]["points"][1]["value"] == 110.0
    with engine.begin() as c:
        c.execute(
            db.monthly_snapshots.update()
            .where(db.monthly_snapshots.c.month == NEXT)
            .values(regular=360)
        )
    refresh_index(engine, AS_OF)
    assert read(client, monkeypatch)["categories"][0]["points"][1]["value"] == 120.0


def test_overall_is_product_mean_and_does_not_average_category_indices(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(engine, 60)
    with engine.begin() as c:
        c.execute(
            db.products.update()
            .where(db.products.c.barcode <= f"{10:013d}")
            .values(category_code=2)
        )
        c.execute(
            db.monthly_snapshots.update()
            .where(
                db.monthly_snapshots.c.month == NEXT, db.monthly_snapshots.c.barcode <= f"{10:013d}"
            )
            .values(regular=600)
        )
    refresh_index(engine, AS_OF)
    result = read(client, monkeypatch)
    assert result["categories"][0]["points"][1]["value"] == round(
        100 * (1.1**50 * 2**10) ** (1 / 60), 4
    )
    assert result["categories"][2]["points"][1]["value"] is None


def test_future_lists_and_months_are_ignored(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(engine)
    with engine.begin() as c:
        c.execute(db.prices_current.update().values(list_date=date(2026, 10, 16)))
        c.execute(
            db.monthly_snapshots.insert().values(
                format_id=1, barcode=f"{1:013d}", month=date(2026, 11, 1), regular=1
            )
        )
    refresh_index(engine, AS_OF)
    result = read(client, monkeypatch)
    point = result["categories"][0]["points"][-1]
    assert point["n_products"] == 0 and point["n_excluded"] == 30
    assert point["value"] is None and point["month"] == CURRENT.isoformat()


def test_index_static_export_equals_rest_with_completed_and_provisional_points(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seed(engine, extra=[(0, 330), (300, None)])
    refresh_index(engine, AS_OF)
    monkeypatch.setattr("korpa_api.export_static.belgrade_today", lambda: AS_OF)
    asyncio.run(export(tmp_path))
    assert json.loads((tmp_path / "index.json").read_text("utf-8")) == read(client, monkeypatch)


def test_no_monthly_history_is_dated_and_unpublished(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    refresh_index(engine, AS_OF)
    result = read(client, monkeypatch)
    assert result["base_month"] == CURRENT.isoformat()
    assert all(
        p["value"] is None and p["n_products"] == 0
        for cat in result["categories"]
        for p in cat["points"]
    )


def test_index_problem_contract(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(*args: object, **kwargs: object) -> None:
        raise ConnectionRefusedError("private")

    monkeypatch.setattr("korpa_api.analytics.price_index", fail)
    response = client.get("/api/index")
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert "private" not in response.text
    from korpa_api.main import app

    responses = app.openapi()["paths"]["/api/index"]["get"]["responses"]
    for status in ("422", "500", "503"):
        assert set(responses[status]["content"]) == {"application/problem+json"}
