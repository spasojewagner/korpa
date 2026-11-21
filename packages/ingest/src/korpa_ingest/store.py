"""Atomic, serialized per-retailer writes with a hard database storage guard."""

import logging
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import cast

import sqlalchemy as sa
from psycopg import Connection as PgConnection
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection, Engine

from korpa_ingest import db
from korpa_ingest.compat import PROFILE, STRICT_PROFILE
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


def validators(
    engine: Engine,
    source: RetailerSource,
    profile: str = PROFILE,
) -> tuple[str | None, str | None]:
    with engine.connect() as connection:
        row = (
            connection.execute(
                sa.select(db.retailers).where(
                    db.retailers.c.slug == source.slug,
                    db.retailers.c.resource_url == source.url,
                    db.retailers.c.validator_profile == profile,
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None, None
        return row["last_etag"], row["last_modified"]


def _write_rows(
    connection: Connection,
    retailer_id: int,
    rows: list[PriceRow],
    *,
    write_current: bool = True,
) -> None:
    if not rows:
        return
    connection.exec_driver_sql("""
        CREATE TEMP TABLE ingest_stage (
            seq integer, category integer, category_name text, name text, brand text,
            barcode text, unit text, format_name text, list_date date, regular integer,
            unit_price integer, discounted integer, disc_from date, disc_to date,
            vat integer, kind text
        ) ON COMMIT DROP
    """)
    raw = cast(PgConnection[tuple[object, ...]], connection.connection.driver_connection)
    with raw.cursor() as cursor, cursor.copy("COPY ingest_stage FROM STDIN") as copy:
        for seq, row in enumerate(rows):
            copy.write_row(
                (
                    seq,
                    row.category,
                    row.category_name,
                    row.name,
                    row.brand,
                    row.barcode,
                    row.unit,
                    row.format_name,
                    row.list_date,
                    row.regular,
                    row.unit_price,
                    row.discounted,
                    row.disc_from,
                    row.disc_to,
                    row.vat,
                    row.kind,
                )
            )
    params = {"retailer_id": retailer_id}
    statements = (
        """INSERT INTO categories (code, name)
           SELECT DISTINCT ON (category) category, category_name FROM ingest_stage
           ORDER BY category, seq DESC ON CONFLICT (code) DO NOTHING""",
        """INSERT INTO products (barcode, name, brand, unit, category_code, search_tsv)
           SELECT DISTINCT ON (barcode) barcode, name, brand, unit, category,
               to_tsvector('simple', name || ' ' || brand)
           FROM ingest_stage ORDER BY barcode, seq DESC ON CONFLICT (barcode) DO NOTHING""",
        """INSERT INTO product_names (barcode, retailer_id, raw_name)
           SELECT DISTINCT ON (barcode) barcode, :retailer_id, name FROM ingest_stage
           ORDER BY barcode, seq DESC
           ON CONFLICT (barcode, retailer_id) DO UPDATE SET raw_name = excluded.raw_name
           WHERE product_names.raw_name IS DISTINCT FROM excluded.raw_name""",
        """INSERT INTO retail_formats (retailer_id, name)
           SELECT DISTINCT :retailer_id, format_name FROM ingest_stage ORDER BY format_name
           ON CONFLICT (retailer_id, name) DO NOTHING""",
        """INSERT INTO monthly_snapshots (format_id, barcode, month, regular, discounted)
           SELECT f.id, s.barcode, s.list_date, s.regular, s.discounted
           FROM ingest_stage s JOIN retail_formats f
             ON f.name = s.format_name AND f.retailer_id = :retailer_id
           WHERE s.kind = 'MESEČNI_PRESEK' ORDER BY f.id, s.barcode, s.list_date
           ON CONFLICT (format_id, barcode, month) DO NOTHING""",
    )
    for statement in statements:
        connection.execute(sa.text(statement), params)
    if not write_current:
        return
    connection.execute(
        sa.text("""
        CREATE TEMP TABLE ingest_current ON COMMIT DROP AS
        SELECT s.*, f.id AS format_id, p.regular AS old_regular,
            p.discounted AS old_discounted, p.barcode IS NOT NULL AS existed
        FROM ingest_stage s JOIN retail_formats f
          ON f.name = s.format_name AND f.retailer_id = :retailer_id
        LEFT JOIN prices_current p ON p.format_id = f.id AND p.barcode = s.barcode
        WHERE s.kind = 'VAŽEĆI_CENOVNIK' AND (p.list_date IS NULL OR s.list_date >= p.list_date)
    """),
        params,
    )
    # Compare every incoming source date to its predecessor before updating current prices.
    connection.execute(
        sa.text("""
        INSERT INTO price_changes (format_id, barcode, changed_on, regular, discounted)
        SELECT format_id, barcode, list_date, regular, discounted FROM (
            SELECT *, row_number() OVER w AS n,
                lag(regular) OVER w AS prev_regular, lag(discounted) OVER w AS prev_discounted
            FROM ingest_current WINDOW w AS (PARTITION BY format_id, barcode ORDER BY list_date)
        ) s WHERE (n = 1 AND (NOT existed OR
                        (regular, discounted) IS DISTINCT FROM (old_regular, old_discounted)))
             OR (n > 1 AND (regular, discounted) IS DISTINCT FROM (prev_regular, prev_discounted))
        ORDER BY format_id, barcode, list_date
        ON CONFLICT (format_id, barcode, changed_on) DO UPDATE
          SET regular = excluded.regular, discounted = excluded.discounted
    """)
    )
    connection.execute(
        sa.text("""
        INSERT INTO prices_current
            (format_id, barcode, regular, discounted, disc_from, disc_to,
             unit_price, vat, list_date)
        SELECT DISTINCT ON (format_id, barcode)
            format_id, barcode, regular, discounted, disc_from, disc_to, unit_price, vat, list_date
        FROM ingest_current ORDER BY format_id, barcode, list_date DESC
        ON CONFLICT (format_id, barcode) DO UPDATE SET
            regular = excluded.regular, discounted = excluded.discounted,
            disc_from = excluded.disc_from, disc_to = excluded.disc_to,
            unit_price = excluded.unit_price, vat = excluded.vat, list_date = excluded.list_date,
            updated_at = now()
        WHERE excluded.list_date >= prices_current.list_date
    """)
    )


def _withdraw(connection: Connection, retailer_id: int, rows: list[PriceRow]) -> None:
    if not rows:
        return
    connection.execute(
        sa.text("""
        DELETE FROM prices_current p USING retail_formats f
        WHERE p.format_id = f.id AND f.retailer_id = :retailer_id
          AND p.list_date <= (SELECT max(list_date) FROM ingest_stage
                              WHERE kind = 'VAŽEĆI_CENOVNIK')
          AND NOT EXISTS (
              SELECT 1 FROM ingest_stage s WHERE s.kind = 'VAŽEĆI_CENOVNIK'
                  AND s.format_name = f.name AND s.barcode = p.barcode
          )
    """),
        {"retailer_id": retailer_id},
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
        previous_retailer = (
            connection.execute(
                sa.select(db.retailers).where(
                    db.retailers.c.slug == source.slug,
                )
            )
            .mappings()
            .first()
        )
        retailer_id_before = previous_retailer["id"] if previous_retailer else None
        previous_run = (
            connection.execute(
                sa.select(db.ingest_runs)
                .where(
                    db.ingest_runs.c.retailer_id == retailer_id_before,
                    db.ingest_runs.c.errors_json["header_accepted"].as_boolean().is_(True),
                    db.ingest_runs.c.errors_json["fully_processed"].as_boolean().is_(True),
                    db.ingest_runs.c.http_status.in_([200, 304]),
                )
                .order_by(db.ingest_runs.c.id.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if download.status == 304 and previous_run is not None:
            # A 304 represents the same processed file, including its quality report and baseline.
            prior = previous_run["errors_json"]
            parsed.report.rows_total = previous_run["rows_total"]
            parsed.report.rows_valid = previous_run["rows_valid"]
            parsed.report.errors = Counter(prior.get("errors", {}))
            parsed.report.errors_by_rule = Counter(prior.get("errors_by_rule", {}))
            parsed.report.deviations = Counter(prior.get("deviations", {}))
            parsed.report.samples = prior.get("sample_lines", {})
            parsed.report.profile = prior.get("profile")
            parsed.header_accepted = prior.get("header_accepted", False)
            parsed.fully_processed = prior.get("fully_processed", False)
            parsed.has_current = prior.get("has_current", False)
        accepted = parsed.header_accepted and parsed.fully_processed
        cacheable = accepted and download.status == 200
        same_url = previous_retailer is not None and previous_retailer["resource_url"] == source.url
        statement = insert(db.retailers).values(
            name=source.name,
            slug=source.slug,
            dataset_id=source.dataset_id,
            resource_url=source.url,
            last_seen_at=datetime.now(UTC),
            last_etag=download.etag
            if cacheable
            else (previous_retailer["last_etag"] if same_url and previous_retailer else None),
            last_modified=download.last_modified
            if cacheable
            else (previous_retailer["last_modified"] if same_url and previous_retailer else None),
            validator_profile=(parsed.report.profile or STRICT_PROFILE)
            if cacheable
            else (
                previous_retailer["validator_profile"] if same_url and previous_retailer else None
            ),
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
                "validator_profile",
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
        shrink = False
        if accepted and parsed.has_current and download.status != 304:
            # Rejected files and 304 audits must not reset the last usable file's shrink baseline.
            baseline = connection.execute(
                sa.select(db.ingest_runs.c.rows_valid)
                .where(
                    db.ingest_runs.c.retailer_id == retailer_id,
                    db.ingest_runs.c.errors_json["header_accepted"].as_boolean().is_(True),
                    db.ingest_runs.c.errors_json["fully_processed"].as_boolean().is_(True),
                    db.ingest_runs.c.errors_json["errors"]["suspicious_shrink"]
                    .as_integer()
                    .is_(None),
                )
                .order_by(db.ingest_runs.c.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            shrink = baseline is not None and parsed.report.rows_valid * 2 < baseline
            if shrink:
                parsed.report.error("suspicious_shrink")
        if accepted and download.status != 304:
            _write_rows(connection, retailer_id, parsed.rows, write_current=not shrink)
            if parsed.has_current and not shrink:
                _withdraw(connection, retailer_id, parsed.rows)
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
                errors_json={
                    **parsed.report.as_dict(),
                    "header_accepted": parsed.header_accepted,
                    "fully_processed": parsed.fully_processed,
                    "has_current": parsed.has_current,
                    "source_url": source.url,
                },
            )
        )
        database_size(connection)


# Per-format monthly snapshots are kept for this many months (current one included); older
# months are folded into monthly_prices, one row per product, so history stays within budget.
KEEP_MONTHS = 3


def month_start(day: date, back: int) -> date:
    """First day of the month `back` months before `day`'s month."""
    ordinal = day.year * 12 + day.month - 1 - back
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def compact_monthly(engine: Engine, today: date, keep_months: int = KEEP_MONTHS) -> int:
    """Fold per-format snapshots older than the window into monthly_prices; returns rows removed.

    Idempotent. Late rows for an already compacted month widen min/max and add to n_formats;
    the stored median is kept as first computed.
    """
    cutoff = month_start(today, keep_months - 1)
    with engine.begin() as connection:
        connection.execute(
            sa.text("""
            INSERT INTO monthly_prices AS m (barcode, month, min_regular, median_regular,
                max_regular, min_discounted, n_formats)
            SELECT barcode, month, min(regular),
                   percentile_disc(0.5) WITHIN GROUP (ORDER BY regular),
                   max(regular), min(discounted), count(*)
            FROM monthly_snapshots WHERE month < :cutoff GROUP BY barcode, month
            ON CONFLICT (barcode, month) DO UPDATE SET
                min_regular = least(m.min_regular, excluded.min_regular),
                max_regular = greatest(m.max_regular, excluded.max_regular),
                min_discounted = least(m.min_discounted, excluded.min_discounted),
                n_formats = m.n_formats + excluded.n_formats
            """),
            {"cutoff": cutoff},
        )
        removed = connection.execute(
            sa.text("DELETE FROM monthly_snapshots WHERE month < :cutoff"), {"cutoff": cutoff}
        ).rowcount
    logger.info("compacted monthly snapshots before %s: %s rows", cutoff, removed)
    return int(removed)
