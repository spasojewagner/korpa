"""Fixed-base Jevons index of median regular prices, excluding undefined relatives."""

from datetime import date

import sqlalchemy as sa
from korpa_ingest import db
from korpa_ingest.store import check_budget
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from korpa_api.schemas import IndexCategory, IndexPoint, IndexResponse

# One calculation for completed months and the on-read provisional point. Integer cross
# multiplication keeps both inclusive ratio boundaries exact; CASE guards division/log(0).
_HISTORY = """
    history AS MATERIALIZED (
        SELECT barcode, month, median_regular FROM monthly_price_history
        WHERE month <= :current_month
    ),
    base AS (SELECT barcode, median_regular AS price FROM history WHERE month = :base_month)
"""
_CALCULATION = """
    , pairs AS (
        SELECT coalesce(m.month, t.month) AS month, coalesce(b.barcode, t.barcode) AS barcode,
               b.price AS base_price, t.price AS target_price
        FROM months m CROSS JOIN base b
        FULL JOIN targets t ON t.month = m.month AND t.barcode = b.barcode
    ), relatives AS (
        SELECT r.month, p.category_code,
            CASE WHEN r.base_price > 0 AND r.target_price > 0
                      AND r.target_price::bigint * 3 >= r.base_price
                      AND r.target_price::bigint <= r.base_price::bigint * 3
                 THEN ln(r.target_price::double precision / r.base_price) END AS log_r
        FROM pairs r JOIN products p USING (barcode)
    ), aggregates AS (
        SELECT month, coalesce(category_code, 0) AS category_code,
               CASE WHEN count(log_r) >= 30 THEN 100 * exp(avg(log_r)) END AS value,
               count(log_r) AS n_products, count(*) - count(log_r) AS n_excluded
        FROM relatives GROUP BY GROUPING SETS ((month, category_code), (month))
    ), codes AS (SELECT code FROM categories UNION ALL SELECT 0)
    SELECT m.month, c.code AS category_code, a.value,
           coalesce(a.n_products, 0) AS n_products, coalesce(a.n_excluded, 0) AS n_excluded
    FROM months m CROSS JOIN codes c
    LEFT JOIN aggregates a ON a.month = m.month AND a.category_code = c.code
"""
_COMPLETED = """
    , targets AS (SELECT barcode, month, median_regular AS price FROM history
                  WHERE month < :current_month),
    months AS (SELECT DISTINCT month FROM targets)
"""
_PROVISIONAL = """
    , targets AS (
        SELECT barcode, CAST(:current_month AS date) AS month,
               percentile_disc(0.5) WITHIN GROUP (ORDER BY regular) AS price
        FROM prices_current WHERE list_date <= :as_of GROUP BY barcode
    ), months AS (SELECT CAST(:current_month AS date) AS month)
"""


def refresh_index(engine: Engine, as_of: date) -> None:
    """Upsert only completed months after compaction; current prices are never stored here."""
    current_month = as_of.replace(day=1)
    with engine.begin() as connection:
        check_budget(connection)
        connection.execute(sa.text("SELECT pg_advisory_xact_lock(41004)"))
        base_month = connection.scalar(
            sa.text("SELECT min(month) FROM monthly_price_history WHERE month <= :month"),
            {"month": current_month},
        )
        # Also removes accidental future/provisional cache rows from older deployments.
        connection.execute(
            db.index_monthly.delete().where(db.index_monthly.c.month >= current_month)
        )
        if base_month is None:
            connection.execute(db.index_monthly.delete())
            return
        connection.execute(
            sa.text(
                "INSERT INTO index_monthly (month, category_code, value, n_products, n_excluded) "
                + "WITH "
                + _HISTORY
                + _COMPLETED
                + _CALCULATION
                + """
            ON CONFLICT (month, category_code) DO UPDATE SET
                value = excluded.value, n_products = excluded.n_products,
                n_excluded = excluded.n_excluded
            """
            ),
            {"base_month": base_month, "current_month": current_month},
        )
        check_budget(connection)


async def price_index(session: AsyncSession, as_of: date) -> IndexResponse:
    """Read the completed-month cache plus an uncached point for today's current prices."""
    current_month = as_of.replace(day=1)
    base_month = await session.scalar(
        sa.text("SELECT min(month) FROM monthly_price_history WHERE month <= :month"),
        {"month": current_month},
    )
    # With no monthly observations there is no base: retain a dated, empty index at this month.
    base_month = base_month or current_month
    names = (
        await session.execute(sa.select(db.categories).order_by(db.categories.c.code))
    ).mappings()
    categories = {0: IndexCategory(code=0, name="Sve kategorije", points=[])}
    categories.update(
        {row["code"]: IndexCategory(code=row["code"], name=row["name"], points=[]) for row in names}
    )
    completed = (
        await session.execute(
            sa.select(db.index_monthly)
            .where(db.index_monthly.c.month >= base_month, db.index_monthly.c.month < current_month)
            .order_by(db.index_monthly.c.month, db.index_monthly.c.category_code)
        )
    ).mappings()
    for row in completed:
        if row["category_code"] in categories:
            categories[row["category_code"]].points.append(
                IndexPoint(
                    month=row["month"],
                    value=row["value"],
                    n_products=row["n_products"],
                    n_excluded=row["n_excluded"],
                    provisional=False,
                )
            )
    provisional = (
        await session.execute(
            sa.text(
                "WITH "
                + _HISTORY.replace("month <= :current_month", "month = :base_month")
                + _PROVISIONAL
                + _CALCULATION
            ),
            {"base_month": base_month, "current_month": current_month, "as_of": as_of},
        )
    ).mappings()
    for row in provisional:
        categories[row["category_code"]].points.append(
            IndexPoint(
                month=row["month"],
                value=round(row["value"], 4) if row["value"] is not None else None,
                n_products=row["n_products"],
                n_excluded=row["n_excluded"],
                provisional=True,
            )
        )
    return IndexResponse(as_of=as_of, base_month=base_month, categories=list(categories.values()))
