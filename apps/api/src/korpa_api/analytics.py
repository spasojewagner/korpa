"""Fixed-base Jevons index of median regular prices, excluding undefined relatives."""

from datetime import date, timedelta
from typing import Literal

import sqlalchemy as sa
from korpa_ingest import db
from korpa_ingest.store import check_budget
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select, Subquery

from korpa_api.pricing import effective_price
from korpa_api.schemas import (
    DiscountAfterJumpSignal,
    IndexCategory,
    IndexPoint,
    IndexResponse,
    SignalItem,
    SignalsParams,
    SignalsResponse,
)

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
        SELECT t.month, t.barcode,
               b.price AS base_price, t.price AS target_price
        FROM base b INNER JOIN targets t ON t.barcode = b.barcode
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
                  WHERE month <= :current_month),
    months AS (SELECT DISTINCT month FROM targets)
"""
_PROVISIONAL = """
    , targets AS (
        SELECT barcode, CAST(:as_of AS date) AS month,
               percentile_disc(0.5) WITHIN GROUP (ORDER BY regular) AS price
        FROM prices_current WHERE list_date <= :as_of GROUP BY barcode
    ), months AS (SELECT CAST(:as_of AS date) AS month)
"""


def refresh_index(engine: Engine, as_of: date) -> None:
    """Upsert final monthly snapshots, including this month; never store current-price points."""
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
            db.index_monthly.delete().where(db.index_monthly.c.month > current_month)
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
            .where(
                db.index_monthly.c.month >= base_month, db.index_monthly.c.month <= current_month
            )
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


def signal_candidates(
    as_of: date, signal_type: Literal["jump", "outlier"] | None = None
) -> Subquery:
    """SQL candidates before response ordering/limits, also usable for read-only audits."""
    p, changes = db.prices_current, db.price_changes
    jumps = (
        sa.select(
            changes.c.format_id,
            changes.c.barcode,
            changes.c.changed_on,
            changes.c.regular,
            sa.func.lag(changes.c.regular)
            .over(
                partition_by=(changes.c.format_id, changes.c.barcode),
                order_by=changes.c.changed_on,
            )
            .label("previous"),
        )
        .where(changes.c.changed_on <= as_of)
        .cte("consecutive_changes")
    )
    jump = sa.select(
        sa.literal("jump").label("type"),
        jumps.c.format_id,
        jumps.c.barcode,
        jumps.c.changed_on.label("date"),
        jumps.c.regular.label("price_para"),
        jumps.c.previous.label("reference_para"),
    ).where(
        jumps.c.changed_on >= as_of - timedelta(days=30),
        jumps.c.previous > 0,
        sa.cast(jumps.c.regular, sa.BigInteger) * 4 >= sa.cast(jumps.c.previous, sa.BigInteger) * 5,
    )
    price = effective_price(p.c.regular, p.c.discounted, p.c.disc_from, p.c.disc_to, as_of)
    # A true outlier necessarily has max >= 1.5 * min in its product. Compute cheap
    # parallelizable bounds first, then sort prices only for potentially unusual products.
    bounds = (
        sa.select(p.c.barcode)
        .where(p.c.list_date <= as_of)
        .group_by(p.c.barcode)
        .having(
            sa.func.count() >= 4,
            sa.func.max(price) > 0,
            sa.cast(sa.func.max(price), sa.BigInteger) * 2
            >= sa.cast(sa.func.min(price), sa.BigInteger) * 3,
        )
        .cte("candidate_products")
        .prefix_with("MATERIALIZED")
    )
    groups = (
        sa.select(
            p.c.barcode,
            sa.func.array_agg(aggregate_order_by(price, price)).label("prices"),
            sa.func.count().label("n"),
        )
        .select_from(p.join(bounds, bounds.c.barcode == p.c.barcode))
        .where(p.c.list_date <= as_of)
        .group_by(p.c.barcode)
        .having(sa.func.count() >= 4)
        .cte("price_groups")
        .prefix_with("MATERIALIZED")
    )
    # For n sorted prices, the lower median of n-1 other formats has rank floor(n/2).
    # Removing a price at/below that rank shifts the reference to the next rank. This
    # handles ties exactly and avoids one median aggregation per current listing.
    rank = groups.c.n.op("/")(2)
    low, high = groups.c.prices[rank], groups.c.prices[rank + 1]
    references = (
        sa.select(
            groups.c.barcode,
            low.label("low"),
            high.label("high"),
        )
        .where(
            sa.cast(groups.c.prices[groups.c.n], sa.BigInteger) * 2
            >= sa.cast(low, sa.BigInteger) * 3
        )
        .cte("other_format_references")
    )
    reference = sa.case((price <= references.c.low, references.c.high), else_=references.c.low)
    outlier = (
        sa.select(
            sa.literal("outlier").label("type"),
            p.c.format_id,
            p.c.barcode,
            p.c.list_date.label("date"),
            price.label("price_para"),
            reference.label("reference_para"),
        )
        .select_from(p.join(references, references.c.barcode == p.c.barcode))
        .where(
            p.c.list_date <= as_of,
            reference > 0,
            sa.cast(price, sa.BigInteger) * 2 >= sa.cast(reference, sa.BigInteger) * 3,
        )
    )
    if signal_type == "jump":
        return jump.subquery("signals")
    if signal_type == "outlier":
        return outlier.subquery("signals")
    return sa.union_all(jump, outlier).subquery("signals")


def signals_statement(as_of: date, params: SignalsParams) -> Select[*tuple[object, ...]]:
    legacy = signal_candidates(as_of, params.type if params.type != "discount_after_jump" else None)
    legacy_rows = sa.select(
        legacy,
        sa.cast(sa.null(), sa.Integer).label("discounted_para"),
        sa.cast(sa.null(), sa.Date).label("disc_from"),
    )
    if params.type == "discount_after_jump":
        candidates = discount_after_jump_candidates(as_of).subquery("published_signals")
    elif params.type is None:
        candidates = sa.union_all(legacy_rows, discount_after_jump_candidates(as_of)).subquery(
            "published_signals"
        )
    else:
        candidates = legacy_rows.subquery("published_signals")
    ratio = sa.cast(candidates.c.price_para, sa.Numeric) / candidates.c.reference_para
    p, f, r = db.products, db.retail_formats, db.retailers
    return (
        sa.select(
            candidates.c.type,
            candidates.c.barcode,
            p.c.name,
            r.c.name.label("retailer"),
            f.c.name.label("format"),
            candidates.c.date,
            candidates.c.price_para,
            candidates.c.reference_para,
            candidates.c.discounted_para,
            candidates.c.disc_from,
            sa.func.round(
                sa.cast(candidates.c.price_para, sa.Numeric)
                / sa.func.nullif(candidates.c.reference_para, 0),
                2,
            ).label("ratio"),
        )
        .select_from(
            candidates.join(p, p.c.barcode == candidates.c.barcode)
            .join(f, f.c.id == candidates.c.format_id)
            .join(r, r.c.id == f.c.retailer_id)
        )
        .where(
            sa.cast(candidates.c.price_para, sa.BigInteger)
            <= sa.cast(candidates.c.reference_para, sa.BigInteger) * 3
        )
        .order_by(
            candidates.c.date.desc(),
            ratio.desc(),
            candidates.c.barcode,
            candidates.c.type,
            candidates.c.format_id,
        )
        .limit(params.limit)
    )


async def signals(session: AsyncSession, params: SignalsParams, as_of: date) -> SignalsResponse:
    # Sort each product's small price group inside the aggregate. A global incremental
    # sort of effective prices adds avoidable work on PostgreSQL 16.
    await session.execute(sa.text("SET LOCAL enable_presorted_aggregate = off"))
    rows = (await session.execute(signals_statement(as_of, params))).mappings()
    items: list[SignalItem | DiscountAfterJumpSignal] = []
    for row in rows:
        if row["type"] == "discount_after_jump":
            items.append(
                DiscountAfterJumpSignal.model_validate(
                    {
                        **row,
                        "old_regular_para": row["reference_para"],
                        "new_regular_para": row["price_para"],
                        "rise_date": row["date"],
                        "as_of": as_of,
                    }
                )
            )
        else:
            items.append(SignalItem.model_validate(row))
    return SignalsResponse(as_of=as_of, items=items)


def discount_after_jump_candidates(as_of: date) -> Select[*tuple[object, ...]]:
    """Active discounts following consecutive regular-price rises in the preceding 60 days."""
    p, changes = db.prices_current, db.price_changes
    history = (
        sa.select(
            changes.c.format_id,
            changes.c.barcode,
            changes.c.changed_on,
            changes.c.regular,
            sa.func.lag(changes.c.regular)
            .over(
                partition_by=(changes.c.format_id, changes.c.barcode),
                order_by=changes.c.changed_on,
            )
            .label("previous"),
        )
        .where(changes.c.changed_on <= as_of)
        .cte("discount_history")
    )
    qualifying = (
        sa.select(
            sa.literal("discount_after_jump").label("type"),
            history.c.format_id,
            history.c.barcode,
            history.c.changed_on.label("date"),
            history.c.regular.label("price_para"),
            history.c.previous.label("reference_para"),
            p.c.discounted.label("discounted_para"),
            p.c.disc_from,
        )
        .select_from(
            history.join(
                p,
                sa.and_(
                    p.c.format_id == history.c.format_id,
                    p.c.barcode == history.c.barcode,
                ),
            )
        )
        .where(
            p.c.list_date <= as_of,
            p.c.discounted.is_not(None),
            p.c.disc_from <= as_of,
            sa.or_(p.c.disc_to.is_(None), p.c.disc_to >= as_of),
            history.c.changed_on >= p.c.disc_from - 60,
            history.c.changed_on < p.c.disc_from,
            history.c.previous > 0,
            sa.cast(history.c.regular, sa.BigInteger) * 5
            >= sa.cast(history.c.previous, sa.BigInteger) * 6,
            sa.cast(history.c.regular, sa.BigInteger)
            <= sa.cast(history.c.previous, sa.BigInteger) * 3,
            sa.cast(p.c.discounted, sa.BigInteger) * 100
            >= sa.cast(history.c.previous, sa.BigInteger) * 98,
        )
    )

    qualified = qualifying.subquery("qualifying_discount_rises")
    ranked = sa.select(
        *qualified.c,
        sa.func.row_number().over(
            partition_by=(qualified.c.format_id, qualified.c.barcode),
            order_by=qualified.c.date.desc(),
        ).label("rank"),
    ).subquery("ranked_discount_rises")
    return sa.select(*(ranked.c[key] for key in qualified.c.keys())).where(ranked.c.rank == 1)


async def suspected_price_errors(session: AsyncSession, as_of: date) -> dict[int, int]:
    """Count above-bound rule candidates per retailer, before any publication limits."""
    candidates = signal_candidates(as_of)
    f = db.retail_formats
    await session.execute(sa.text("SET LOCAL enable_presorted_aggregate = off"))
    rows = await session.execute(
        sa.select(f.c.retailer_id, sa.func.count())
        .select_from(candidates.join(f, f.c.id == candidates.c.format_id))
        .where(
            sa.cast(candidates.c.price_para, sa.BigInteger)
            > sa.cast(candidates.c.reference_para, sa.BigInteger) * 3
        )
        .group_by(f.c.retailer_id)
    )
    return {int(row["retailer_id"]): int(row["count"]) for row in rows.mappings()}
