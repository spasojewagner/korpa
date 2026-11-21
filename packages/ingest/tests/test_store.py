import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from korpa_ingest import db
from korpa_ingest.compat import LEGACY_PROFILE, PROFILE
from korpa_ingest.normalize import normalize
from korpa_ingest.portal import Download, RetailerSource
from korpa_ingest.reader import Parsed, Report, read_csv
from korpa_ingest.store import (
    StorageLimitError,
    compact_monthly,
    month_start,
    persist,
    validators,
)
from sqlalchemy.engine import Engine

SOURCE = RetailerSource("demo", "Demo", "dataset-id", "https://example.org/cene.csv", "sodl")
DOWNLOAD = Download(200, b"", '"etag"', "Fri, 20 Nov 2026 00:00:00 GMT")
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL korpa_test database")
    assert sa.engine.make_url(url).database == "korpa_test", (
        "Tests require a dedicated korpa_test DB"
    )
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
        check=True,
        env=env,
    )
    instance = sa.create_engine(url)
    yield instance
    instance.dispose()


@pytest.fixture(autouse=True)
def clean_database(engine: Engine) -> None:
    with engine.begin() as connection:
        for table in reversed(db.metadata.sorted_tables):
            connection.execute(table.delete())


def fixture_rows() -> Parsed:
    parsed = normalize(read_csv((FIXTURES / "good.csv").read_bytes(), profile=PROFILE))
    today = date.today()
    parsed.rows = [
        row.model_copy(
            update={
                "list_date": today if row.kind == "VAŽEĆI_CENOVNIK" else today.replace(day=1),
            }
        )
        for row in parsed.rows
    ]
    return parsed


def count(engine: Engine, table: sa.Table) -> int:
    with engine.connect() as connection:
        return int(connection.execute(sa.select(sa.func.count()).select_from(table)).scalar_one())


def test_idempotence_and_price_changes(engine: Engine) -> None:
    parsed = fixture_rows()
    for _ in range(2):
        persist(engine, SOURCE, parsed, DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.products) == 1
    assert count(engine, db.prices_current) == 1
    assert count(engine, db.monthly_snapshots) == 1
    assert count(engine, db.price_changes) == 1
    assert count(engine, db.ingest_runs) == 2
    current = next(row for row in parsed.rows if row.kind == "VAŽEĆI_CENOVNIK")
    changed = current.model_copy(
        update={"regular": 13500, "list_date": date.today() + timedelta(1)}
    )
    persist(
        engine,
        SOURCE,
        Parsed([changed], Report(1, 1, profile=PROFILE), True, True, True),
        DOWNLOAD,
        datetime.now(UTC),
    )
    assert count(engine, db.price_changes) == 2
    with engine.connect() as connection:
        assert connection.execute(sa.select(db.prices_current.c.regular)).scalar_one() == 13500
    assert validators(engine, SOURCE) == (DOWNLOAD.etag, DOWNLOAD.last_modified)


def test_unchanged_price_new_date_does_not_append_history(engine: Engine) -> None:
    parsed = fixture_rows()
    persist(engine, SOURCE, parsed, DOWNLOAD, datetime.now(UTC))
    parsed.rows = [
        row.model_copy(update={"list_date": date.today() + timedelta(1)})
        for row in parsed.rows
        if row.kind == "VAŽEĆI_CENOVNIK"
    ]
    persist(engine, SOURCE, parsed, DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.price_changes) == 1


def test_stale_import_cannot_revert_current_and_monthly_is_permanent(engine: Engine) -> None:
    parsed = fixture_rows()
    persist(engine, SOURCE, parsed, DOWNLOAD, datetime.now(UTC))
    parsed.rows = [
        row.model_copy(
            update={
                "regular": 999999,
                "list_date": row.list_date - timedelta(1)
                if row.kind == "VAŽEĆI_CENOVNIK"
                else row.list_date,
            }
        )
        for row in parsed.rows
    ]
    persist(engine, SOURCE, parsed, DOWNLOAD, datetime.now(UTC))
    with engine.connect() as connection:
        assert connection.execute(sa.select(db.prices_current.c.regular)).scalar_one() == 12999
        assert connection.execute(sa.select(db.monthly_snapshots.c.regular)).scalar_one() == 12999


def test_mixed_report_and_304_are_audited(engine: Engine) -> None:
    parsed = normalize(read_csv((FIXTURES / "mixed.csv").read_bytes(), profile=PROFILE))
    persist(engine, SOURCE, parsed, DOWNLOAD, datetime.now(UTC))
    assert validators(engine, SOURCE) == (DOWNLOAD.etag, DOWNLOAD.last_modified)
    with engine.connect() as connection:
        report = connection.execute(sa.select(db.ingest_runs)).mappings().one()
        assert report["rows_total"] == 3
        assert report["rows_valid"] == 2
        assert report["errors_json"]["errors"] == {"barcode": 1}
    persist(engine, SOURCE, Parsed([], Report()), Download(304, b""), datetime.now(UTC))
    assert count(engine, db.ingest_runs) == 2


def test_storage_limit_prevents_every_write(engine: Engine) -> None:
    with patch("korpa_ingest.store.database_size", return_value=900_000_000):
        with pytest.raises(StorageLimitError):
            persist(engine, SOURCE, fixture_rows(), DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.retailers) == 0
    assert count(engine, db.ingest_runs) == 0


def test_failure_rolls_back_all_dimensions_and_prices(engine: Engine) -> None:
    with patch("korpa_ingest.store._write_rows", side_effect=RuntimeError("failed")):
        with pytest.raises(RuntimeError):
            persist(engine, SOURCE, fixture_rows(), DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.retailers) == 0


def test_retention_keeps_monthly_history(engine: Engine) -> None:
    parsed = fixture_rows()
    parsed.rows = [
        row.model_copy(
            update={
                "list_date": date.today() - timedelta(days=121),
            }
        )
        if row.kind == "VAŽEĆI_CENOVNIK"
        else row
        for row in parsed.rows
    ]
    persist(engine, SOURCE, parsed, DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.price_changes) == 0
    assert count(engine, db.monthly_snapshots) == 1


def current_file(n: int, *, regular: int = 10000, day: date | None = None) -> Parsed:
    row = next(row for row in fixture_rows().rows if row.kind == "VAŽEĆI_CENOVNIK")
    rows = [
        row.model_copy(
            update={
                "barcode": f"{i:013d}",
                "regular": regular,
                "list_date": day or date.today(),
            }
        )
        for i in range(1, n + 1)
    ]
    return Parsed(rows, Report(n, n, profile=PROFILE), True, True, True)


def test_withdrawals_remove_only_missing_current_listings(engine: Engine) -> None:
    initial = current_file(3)
    # A withdrawn product's monthly observation must survive too.
    initial.rows.append(
        initial.rows[-1].model_copy(
            update={
                "kind": "MESEČNI_PRESEK",
                "list_date": date.today().replace(day=1),
            }
        )
    )
    initial.report.rows_total += 1
    initial.report.rows_valid += 1
    persist(engine, SOURCE, initial, DOWNLOAD, datetime.now(UTC))
    initial_history = count(engine, db.price_changes)
    replacement = current_file(2)
    persist(engine, SOURCE, replacement, DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.prices_current) == 2
    assert count(engine, db.price_changes) == initial_history
    assert count(engine, db.monthly_snapshots) == 1
    assert not replacement.report.errors  # exactly 50% is accepted


def test_suspicious_shrink_keeps_prices_and_history(engine: Engine) -> None:
    persist(engine, SOURCE, current_file(5), DOWNLOAD, datetime.now(UTC))
    replacement = current_file(2, regular=99999)
    persist(engine, SOURCE, replacement, DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.prices_current) == 5
    assert count(engine, db.price_changes) == 5
    assert replacement.report.rows_valid == 2
    assert replacement.report.errors == {"suspicious_shrink": 1}
    with engine.connect() as c:
        assert set(c.execute(sa.select(db.prices_current.c.regular)).scalars()) == {10000}
    # Repeated bad imports cannot lower the baseline and bypass protection.
    again = current_file(2, regular=99999)
    persist(engine, SOURCE, again, DOWNLOAD, datetime.now(UTC))
    assert again.report.errors == {"suspicious_shrink": 1}
    assert count(engine, db.prices_current) == 5


def test_bad_header_and_monthly_only_files_cannot_withdraw(engine: Engine) -> None:
    persist(engine, SOURCE, current_file(4), DOWNLOAD, datetime.now(UTC))
    rejected = Parsed([], Report(4, 0, profile=PROFILE))
    rejected.report.error("header", count=4)
    persist(engine, SOURCE, rejected, Download(200, b"", '"bad"'), datetime.now(UTC))
    assert count(engine, db.prices_current) == 4
    monthly = fixture_rows()
    monthly.rows = [r for r in monthly.rows if r.kind == "MESEČNI_PRESEK"]
    monthly.has_current = False
    monthly.report.rows_valid = 1
    persist(engine, SOURCE, monthly, DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.prices_current) == 4
    assert count(engine, db.monthly_snapshots) == 1


def test_withdrawals_do_not_touch_other_retailers_or_newer_prices(engine: Engine) -> None:
    other = RetailerSource("other", "Other", "other-id", "https://example.org/other.csv", "sodl")
    persist(engine, SOURCE, current_file(4), DOWNLOAD, datetime.now(UTC))
    persist(engine, other, current_file(4), DOWNLOAD, datetime.now(UTC))
    stale = current_file(2, day=date.today() - timedelta(1))
    persist(engine, SOURCE, stale, DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.prices_current) == 8


def test_validator_profile_and_rejected_file_do_not_poison_cache(engine: Engine) -> None:
    persist(engine, SOURCE, current_file(1), DOWNLOAD, datetime.now(UTC))
    assert validators(engine, SOURCE) == (DOWNLOAD.etag, DOWNLOAD.last_modified)
    assert validators(engine, SOURCE, profile="future-profile") == (None, None)
    rejected = Parsed([], Report(profile=PROFILE))
    rejected.report.error("encoding")
    persist(engine, SOURCE, rejected, Download(200, b"", '"bad"'), datetime.now(UTC))
    assert validators(engine, SOURCE) == (DOWNLOAD.etag, DOWNLOAD.last_modified)
    changed_url = RetailerSource(
        "demo", "Demo", "dataset-id", "https://example.org/new.csv", "sodl"
    )
    assert validators(engine, changed_url) == (None, None)


def test_profile_two_ignores_the_previous_profiles_validators(engine: Engine) -> None:
    legacy = current_file(1)
    legacy.report.profile = LEGACY_PROFILE
    persist(engine, SOURCE, legacy, DOWNLOAD, datetime.now(UTC))
    assert validators(engine, SOURCE, profile=LEGACY_PROFILE) == (
        DOWNLOAD.etag,
        DOWNLOAD.last_modified,
    )
    assert validators(engine, SOURCE) == (None, None)


def test_304_retains_report_validators_and_withdrawal_baseline(engine: Engine) -> None:
    initial = current_file(5)
    initial.report.deviations["unit_case"] = 5
    persist(engine, SOURCE, initial, DOWNLOAD, datetime.now(UTC))
    audit = Parsed([], Report(profile=PROFILE))
    persist(engine, SOURCE, audit, Download(304, b""), datetime.now(UTC))
    assert audit.report.rows_valid == 5
    assert audit.report.deviations == {"unit_case": 5}
    assert validators(engine, SOURCE) == (DOWNLOAD.etag, DOWNLOAD.last_modified)
    shrink = current_file(2)
    persist(engine, SOURCE, shrink, DOWNLOAD, datetime.now(UTC))
    assert shrink.report.errors == {"suspicious_shrink": 1}
    assert count(engine, db.prices_current) == 5


def test_304_uses_cached_file_report_after_an_intervening_download_failure(engine: Engine) -> None:
    persist(engine, SOURCE, current_file(5), DOWNLOAD, datetime.now(UTC))
    failed = Parsed([], Report(profile=PROFILE))
    failed.report.error("download")
    persist(engine, SOURCE, failed, Download(503, b""), datetime.now(UTC))
    cached = Parsed([], Report(profile=PROFILE))
    persist(engine, SOURCE, cached, Download(304, b""), datetime.now(UTC))
    assert cached.report.rows_valid == 5
    assert not cached.report.errors
    assert count(engine, db.prices_current) == 5


def test_set_based_history_keeps_all_changed_dates(engine: Engine) -> None:
    initial = current_file(1)
    persist(engine, SOURCE, initial, DOWNLOAD, datetime.now(UTC))
    base = initial.rows[0]
    rows = [
        base.model_copy(update={"regular": price, "list_date": date.today() + timedelta(days=i)})
        for i, price in enumerate([10000, 11000, 11000, 12000])
    ]
    incoming = Parsed(rows, Report(4, 4, profile=PROFILE), True, True, True)
    persist(engine, SOURCE, incoming, DOWNLOAD, datetime.now(UTC))
    assert count(engine, db.price_changes) == 3
    with engine.connect() as c:
        assert c.execute(sa.select(db.prices_current.c.regular)).scalar_one() == 12000


def test_monthly_compaction_keeps_recent_detail_and_folds_older_months(engine: Engine) -> None:
    persist(engine, SOURCE, fixture_rows(), DOWNLOAD, datetime.now(UTC))
    with engine.begin() as connection:
        format_id, barcode = connection.execute(
            sa.select(db.monthly_snapshots.c.format_id, db.monthly_snapshots.c.barcode)
        ).first()
        other = connection.execute(
            db.retail_formats.insert()
            .values(retailer_id=sa.select(db.retailers.c.id).scalar_subquery(), name="Drugi")
            .returning(db.retail_formats.c.id)
        ).scalar_one()
        old = date(2026, 5, 1)
        connection.execute(
            db.monthly_snapshots.insert(),
            [
                {
                    "format_id": format_id,
                    "barcode": barcode,
                    "month": old,
                    "regular": 100,
                    "discounted": 90,
                },
                {
                    "format_id": other,
                    "barcode": barcode,
                    "month": old,
                    "regular": 300,
                    "discounted": None,
                },
            ],
        )
    recent = count(engine, db.monthly_snapshots) - 2
    assert compact_monthly(engine, date(2026, 11, 21)) == 2
    assert compact_monthly(engine, date(2026, 11, 21)) == 0
    assert count(engine, db.monthly_snapshots) == recent
    with engine.connect() as connection:
        row = connection.execute(sa.select(db.monthly_prices)).mappings().one()
        history = (
            connection.execute(
                sa.select(db.monthly_price_history).where(
                    db.monthly_price_history.c.barcode == barcode
                )
            )
            .mappings()
            .all()
        )
    assert (
        row["month"],
        row["min_regular"],
        row["max_regular"],
        row["min_discounted"],
        row["n_formats"],
    ) == (old, 100, 300, 90, 2)
    assert row["median_regular"] in {100, 300}
    assert {h["month"] for h in history} >= {old}
    assert len([h for h in history if h["month"] == old]) == 1


def test_month_start() -> None:
    assert month_start(date(2026, 11, 21), 0) == date(2026, 11, 1)
    assert month_start(date(2026, 11, 21), 2) == date(2026, 9, 1)
    assert month_start(date(2026, 1, 5), 1) == date(2025, 12, 1)
