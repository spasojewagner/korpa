import re
from datetime import date

import sqlalchemy as sa
from korpa_ingest import db
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from korpa_api.pricing import effective_price
from korpa_api.schemas import (
    BasketFormat,
    BasketRequest,
    BasketResponse,
    BasketRetailer,
    CategoryItem,
    QualityItem,
    QualityResponse,
    SearchItem,
    SearchParams,
    SearchResponse,
)
from korpa_api.translit import normalize_query


def search_statements(
    params: SearchParams, as_of: date
) -> tuple[Select[int], Select[*tuple[object, ...]]]:
    p, prices = db.products, db.prices_current
    query = normalize_query(params.q)
    config = sa.literal_column("'simple'::regconfig", type_=sa.Text())
    rank = sa.func.ts_rank(p.c.search_tsv, sa.func.plainto_tsquery(config, query))
    similarity = sa.func.similarity(p.c.search_norm, query)
    if re.fullmatch(r"[0-9]{13}", params.q):
        condition = p.c.barcode == params.q
    else:
        condition = sa.or_(
            p.c.search_tsv.op("@@")(sa.func.plainto_tsquery(config, query)),
            p.c.search_norm.op("%>")(query),
        )
    if params.category is not None:
        condition = sa.and_(condition, p.c.category_code == params.category)
    matches = sa.select(p, (rank + similarity).label("score")).where(condition).cte("matches")
    count = sa.select(sa.func.count()).select_from(matches)
    page = (
        sa.select(matches)
        .order_by(
            matches.c.score.desc(),
            matches.c.name,
            matches.c.barcode,
        )
        .limit(params.limit)
        .offset(params.offset)
        .cte("page")
    )
    effective = effective_price(
        prices.c.regular,
        prices.c.discounted,
        prices.c.disc_from,
        prices.c.disc_to,
        as_of,
    )
    aggregate = (
        sa.select(
            sa.func.min(effective).label("min_effective_para"),
            sa.func.max(effective).label("max_effective_para"),
            sa.func.count().label("n_formats"),
            sa.func.coalesce(sa.func.bool_or(effective < prices.c.regular), False).label(
                "any_discount"
            ),
            sa.func.max(prices.c.list_date).label("list_date"),
        )
        .where(prices.c.barcode == page.c.barcode)
        .lateral("price_summary")
    )
    items = (
        sa.select(
            page.c.barcode,
            page.c.name,
            page.c.brand,
            page.c.unit,
            page.c.category_code,
            aggregate.c.min_effective_para,
            aggregate.c.max_effective_para,
            aggregate.c.n_formats,
            aggregate.c.any_discount,
            aggregate.c.list_date,
        )
        .select_from(page.join(aggregate, sa.true()))
        .order_by(
            page.c.score.desc(),
            page.c.name,
            page.c.barcode,
        )
    )
    return count, items


async def search(session: AsyncSession, params: SearchParams, as_of: date) -> SearchResponse:
    # Local setting resets when the request's read transaction finishes.
    await session.execute(sa.text("SET LOCAL pg_trgm.word_similarity_threshold = 0.3"))
    count, items = search_statements(params, as_of)
    total = int((await session.execute(count)).scalar_one())
    rows = (await session.execute(items)).mappings()
    return SearchResponse(
        items=[SearchItem.model_validate(row) for row in rows], total=total, as_of=as_of
    )


def basket_statement(request: BasketRequest, as_of: date) -> Select[*tuple[object, ...]]:
    prices, formats, retailers = db.prices_current, db.retail_formats, db.retailers
    requested = (
        sa.values(
            sa.column("barcode", sa.CHAR(13)),
            sa.column("qty", sa.Integer),
            name="requested",
        )
        .data([(item.barcode, item.qty) for item in request.items])
        .cte()
    )
    effective = effective_price(
        prices.c.regular,
        prices.c.discounted,
        prices.c.disc_from,
        prices.c.disc_to,
        as_of,
    )
    summary = (
        sa.select(
            prices.c.format_id,
            sa.func.sum(sa.cast(effective, sa.BigInteger) * requested.c.qty).label("total_para"),
            sa.func.array_agg(prices.c.barcode).label("found"),
            sa.func.min(prices.c.list_date).label("list_date_min"),
            sa.func.max(prices.c.list_date).label("list_date_max"),
        )
        .select_from(
            prices.join(requested, prices.c.barcode == sa.cast(requested.c.barcode, sa.CHAR(13)))
        )
        .group_by(
            prices.c.format_id,
        )
        .cte("basket_summary")
    )
    statement = sa.select(
        formats.c.id,
        formats.c.name,
        retailers.c.id.label("retailer_id"),
        retailers.c.name.label("retailer_name"),
        retailers.c.slug,
        sa.func.coalesce(summary.c.total_para, 0).label("total_para"),
        summary.c.found,
        summary.c.list_date_min,
        summary.c.list_date_max,
    ).select_from(formats.join(retailers).outerjoin(summary, summary.c.format_id == formats.c.id))
    return statement


async def basket(session: AsyncSession, request: BasketRequest, as_of: date) -> BasketResponse:
    statement = basket_statement(request, as_of)
    rows = list((await session.execute(statement)).mappings())
    barcodes = [item.barcode for item in request.items]

    def key(row: RowMapping) -> tuple[bool, int, int, str, int]:
        found = set(row["found"] or [])
        complete = len(found) == len(barcodes)
        return (
            not complete,
            0 if complete else -len(found),
            row["total_para"],
            row["name"],
            row["id"],
        )

    grouped: dict[int, BasketRetailer] = {}
    for rank, row in enumerate(sorted(rows, key=key), start=1):
        found = set(row["found"] or [])
        retailer_id = row["retailer_id"]
        group = grouped.setdefault(
            retailer_id,
            BasketRetailer(
                id=retailer_id,
                name=row["retailer_name"],
                slug=row["slug"],
                formats=[],
            ),
        )
        group.formats.append(
            BasketFormat(
                id=row["id"],
                name=row["name"],
                total_para=row["total_para"],
                found_barcodes=[b for b in barcodes if b in found],
                missing_barcodes=[b for b in barcodes if b not in found],
                complete=len(found) == len(barcodes),
                rank=rank,
                list_date_min=row["list_date_min"],
                list_date_max=row["list_date_max"],
            )
        )
    return BasketResponse(retailers=list(grouped.values()), as_of=as_of)


async def categories(session: AsyncSession) -> list[CategoryItem]:
    rows = (
        await session.execute(
            sa.select(
                db.categories.c.code,
                db.categories.c.name,
                sa.func.count(db.products.c.barcode).label("n_products"),
            )
            .select_from(db.categories.outerjoin(db.products))
            .group_by(
                db.categories.c.code,
                db.categories.c.name,
            )
            .order_by(db.categories.c.code)
        )
    ).mappings()
    return [CategoryItem.model_validate(row) for row in rows]


async def quality(session: AsyncSession, as_of: date) -> QualityResponse:
    r, runs = db.retailers, db.ingest_runs
    latest = (
        sa.select(runs)
        .where(runs.c.retailer_id == r.c.id)
        .order_by(
            runs.c.id.desc(),
        )
        .limit(1)
        .lateral("latest_run")
    )
    newest = (
        sa.select(sa.func.max(db.prices_current.c.list_date).label("list_date"))
        .select_from(
            db.retail_formats.join(db.prices_current),
        )
        .where(db.retail_formats.c.retailer_id == r.c.id)
        .lateral("newest_list")
    )
    rows = (
        await session.execute(
            sa.select(
                r.c.id,
                r.c.name,
                r.c.slug,
                latest.c.http_status,
                latest.c.rows_total,
                latest.c.rows_valid,
                latest.c.errors_json,
                latest.c.finished_at,
                newest.c.list_date,
            )
            .select_from(r.outerjoin(latest, sa.true()).outerjoin(newest, sa.true()))
            .order_by(r.c.slug)
        )
    ).mappings()
    result: list[QualityItem] = []
    for row in rows:
        report = row["errors_json"] or {}
        errors = report.get("errors", {})
        status = (
            "never"
            if row["finished_at"] is None
            else (
                "ok"
                if not errors and row["http_status"] in (200, 304)
                else ("partial" if row["rows_valid"] else "failed")
            )
        )
        result.append(
            QualityItem.model_validate(
                {
                    **row,
                    "status": status,
                    "errors": errors,
                    "errors_by_rule": report.get("errors_by_rule", {}),
                    "deviations": report.get("deviations", {}),
                    "profile": report.get("profile"),
                    "days_since_list_date": (as_of - row["list_date"]).days
                    if row["list_date"]
                    else None,
                }
            )
        )
    return QualityResponse(retailers=result, as_of=as_of)
