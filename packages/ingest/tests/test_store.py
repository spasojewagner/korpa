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
from korpa_ingest.normalize import normalize
from korpa_ingest.portal import Download, RetailerSource
from korpa_ingest.reader import Parsed, Report, read_csv
from korpa_ingest.store import StorageLimitError, persist, validators
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
    parsed = normalize(read_csv((FIXTURES / "good.csv").read_bytes()))
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
    persist(engine, SOURCE, Parsed([changed], Report(1, 1)), DOWNLOAD, datetime.now(UTC))
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
    parsed = normalize(read_csv((FIXTURES / "mixed.csv").read_bytes()))
    persist(engine, SOURCE, parsed, DOWNLOAD, datetime.now(UTC))
    assert validators(engine, SOURCE) == (None, None)
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
