"""Atomic, serialized per-retailer writes with a hard database storage guard."""

import logging
from datetime import UTC, date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection, Engine

from korpa_ingest import db
from korpa_ingest.portal import Download, RetailerSource
from korpa_ingest.reader import Parsed, PriceRow

logger = logging.getLogger(__name__)
BUDGET_BYTES = 1_000_000_000


class StorageLimitError(RuntimeError):
    pass


def database_size(connection: Connection) -> int:
    size = int(
        connection.execute(sa.text("SELECT pg_database_size(current_database())")).scalar_one()
    )
    logger.info("pg_database_size=%d budget=%d", size, BUDGET_BYTES)
    if size >= BUDGET_BYTES * 0.7:
        logger.warning("Database storage is at least 70%% of budget: %d bytes", size)
    return size


def check_budget(connection: Connection) -> None:
    if database_size(connection) >= BUDGET_BYTES * 0.9:
        raise StorageLimitError("Database is at 90% of budget; all ingest writes stopped")


def validators(engine: Engine, source: RetailerSource) -> tuple[str | None, str | None]:
    with engine.connect() as connection:
        row = (
            connection.execute(
                sa.select(db.retailers).where(
                    db.retailers.c.slug == source.slug,
                    db.retailers.c.resource_url == source.url,
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None, None
        return row["last_etag"], row["last_modified"]


def _write_rows(connection: Connection, retailer_id: int, rows: list[PriceRow]) -> None:
    if not rows:
        return
    # Stable dimension order avoids cross-retailer deadlocks.
    for code, name in sorted({row.category: row.category_name for row in rows}.items()):
        connection.execute(
            insert(db.categories).values(code=code, name=name).on_conflict_do_nothing()
        )
    for barcode, row in sorted({row.barcode: row for row in rows}.items()):
        connection.execute(
            insert(db.products)
            .values(
                barcode=barcode,
                name=row.name,
                brand=row.brand,
                unit=row.unit,
                category_code=row.category,
                search_tsv=sa.func.to_tsvector("simple", row.name + " " + row.brand),
            )
            .on_conflict_do_nothing()
        )
        statement = insert(db.product_names).values(
            barcode=barcode,
            retailer_id=retailer_id,
            raw_name=row.name,
        )
        connection.execute(
            statement.on_conflict_do_update(
                index_elements=["barcode", "retailer_id"],
                set_={"raw_name": row.name},
            )
        )
    formats: dict[str, int] = {}
    for name in sorted({row.format_name for row in rows}):
        statement = insert(db.retail_formats).values(retailer_id=retailer_id, name=name)
        formats[name] = int(
            connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["retailer_id", "name"],
                    set_={"name": name},
                ).returning(db.retail_formats.c.id)
            ).scalar_one()
        )
    for row in rows:
        identity = {"format_id": formats[row.format_name], "barcode": row.barcode}
        if row.kind == "MESEČNI_PRESEK":
            connection.execute(
                insert(db.monthly_snapshots)
                .values(
                    **identity,
                    month=row.list_date,
                    regular=row.regular,
                    discounted=row.discounted,
                )
                .on_conflict_do_nothing()
            )
            continue
        old = (
            connection.execute(
                sa.select(db.prices_current).where(
                    db.prices_current.c.format_id == identity["format_id"],
                    db.prices_current.c.barcode == row.barcode,
                )
            )
            .mappings()
            .first()
        )
        if old is not None and old["list_date"] > row.list_date:
            continue
        changed = old is None or (old["regular"], old["discounted"]) != (
            row.regular,
            row.discounted,
        )
        values = {
            **identity,
            "regular": row.regular,
            "discounted": row.discounted,
            "disc_from": row.disc_from,
            "disc_to": row.disc_to,
            "unit_price": row.unit_price,
            "vat": row.vat,
            "list_date": row.list_date,
            "updated_at": datetime.now(UTC),
        }
        statement = insert(db.prices_current).values(**values)
        connection.execute(
            statement.on_conflict_do_update(
                index_elements=["format_id", "barcode"],
                set_=values,
            )
        )
        if changed:
            statement = insert(db.price_changes).values(
                **identity,
                changed_on=row.list_date,
                regular=row.regular,
                discounted=row.discounted,
            )
            connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["format_id", "barcode", "changed_on"],
                    set_={"regular": row.regular, "discounted": row.discounted},
                )
            )


def persist(
    engine: Engine,
    source: RetailerSource,
    parsed: Parsed,
    download: Download,
    started_at: datetime,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            sa.text("SELECT pg_advisory_xact_lock(hashtext(:slug))"), {"slug": source.slug}
        )
        check_budget(connection)
        clean = not parsed.report.errors
        statement = insert(db.retailers).values(
            name=source.name,
            slug=source.slug,
            dataset_id=source.dataset_id,
            resource_url=source.url,
            last_seen_at=datetime.now(UTC),
            last_etag=download.etag if clean else None,
            last_modified=download.last_modified if clean else None,
        )
        updates = {
            key: statement.excluded[key]
            for key in (
                "name",
                "dataset_id",
                "resource_url",
                "last_seen_at",
                "last_etag",
                "last_modified",
            )
        }
        retailer_id = int(
            connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["slug"],
                    set_=updates,
                ).returning(db.retailers.c.id)
            ).scalar_one()
        )
        _write_rows(connection, retailer_id, parsed.rows)
        check_budget(connection)
        connection.execute(
            sa.delete(db.price_changes).where(
                db.price_changes.c.changed_on < date.today() - timedelta(days=120)
            )
        )
        connection.execute(
            db.ingest_runs.insert().values(
                retailer_id=retailer_id,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                http_status=download.status,
                rows_total=parsed.report.rows_total,
                rows_valid=parsed.report.rows_valid,
                errors_json=parsed.report.as_dict(),
            )
        )
        database_size(connection)
