import re
from pathlib import Path
from unittest.mock import patch

import pytest
from korpa_ingest.cli import app
from korpa_ingest.portal import Download, RetailerSource
from test_reader import FIXTURES
from typer.testing import CliRunner, Result


def run_mixed(*args: str) -> Result:
    source = RetailerSource("demo", "Demo", "id", "https://example.org/cene.csv", "sodl")
    with (
        patch("korpa_ingest.cli.create_engine", side_effect=AssertionError("DB touched")),
        patch("korpa_ingest.cli.PortalClient.discover", return_value=[source]),
        patch(
            "korpa_ingest.cli.PortalClient.download",
            return_value=Download(
                200,
                (FIXTURES / "mixed.csv").read_bytes(),
            ),
        ),
    ):
        return CliRunner().invoke(app, ["ingest", "--retailer", "demo", "--dry-run", *args])


def test_dry_run_never_creates_a_database_engine() -> None:
    result = run_mixed()
    assert result.exit_code == 1
    assert '"rows_total": 3' in result.output
    assert '"rows_valid": 2' in result.output
    assert '"barcode": 1' in result.output


def test_selector_is_required_and_mutually_exclusive() -> None:
    runner = CliRunner()
    assert runner.invoke(app, ["ingest"]).exit_code == 2
    assert runner.invoke(app, ["ingest", "--all", "--retailer", "demo"]).exit_code == 2


def test_row_errors_can_be_reported_without_failing() -> None:
    result = run_mixed("--report-row-errors")
    assert result.exit_code == 0
    assert '"barcode": 1' in result.output


@pytest.mark.parametrize("failure", [False, True])
def test_retries_are_in_per_retailer_report(failure: bool) -> None:
    import json

    import httpx
    from korpa_ingest.portal import PortalClient

    source = RetailerSource("demo", "Demo", "id", "https://example.org/cene.csv", "sodl")
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if failure or requests == 1:
            raise httpx.ConnectTimeout("temporary", request=request)
        return httpx.Response(200, content=(FIXTURES / "good.csv").read_bytes())

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        patch("korpa_ingest.cli.PortalClient", return_value=PortalClient(client)),
        patch("korpa_ingest.portal.PortalClient.discover", return_value=[source]),
        patch("korpa_ingest.portal.time.sleep"),
        patch("korpa_ingest.cli.create_engine", side_effect=AssertionError("DB touched")),
    ):
        result = CliRunner().invoke(app, ["ingest", "--retailer", "demo", "--dry-run"])
    assert result.exit_code == (1 if failure else 0), result.output
    report = json.loads(result.output)
    assert report["retries"] == (2 if failure else 1)
    assert report["errors"] == ({"download": 1} if failure else {})


@pytest.mark.parametrize("dry_run", [False, True])
def test_index_refresh_runs_after_compaction_only_for_writes(dry_run: bool) -> None:
    from unittest.mock import MagicMock

    source = RetailerSource("demo", "Demo", "id", "https://example.org/cene.csv", "sodl")
    order = MagicMock()
    with (
        patch("korpa_ingest.cli.create_engine"),
        patch("korpa_ingest.cli.validators", return_value=(None, None)),
        patch("korpa_ingest.cli.persist"),
        patch("korpa_ingest.cli.PortalClient.discover", return_value=[source]),
        patch(
            "korpa_ingest.cli.PortalClient.download",
            return_value=Download(200, (FIXTURES / "good.csv").read_bytes()),
        ),
        patch("korpa_ingest.cli.compact_monthly") as compact,
    ):
        order.attach_mock(compact, "compact")
        result = CliRunner().invoke(
            app, ["ingest", "--retailer", "demo"] + (["--dry-run"] if dry_run else [])
        )
    assert result.exit_code == 0, result.output
    assert [call[0] for call in order.mock_calls] == ([] if dry_run else ["compact"])


def test_ingest_package_does_not_import_the_api_package() -> None:
    # Layering: the API reads what ingest writes; ingest never depends on the API.
    source = Path(__file__).parents[1] / "src" / "korpa_ingest"
    imports = re.compile(r"^\s*(from|import)\s+korpa_api\b", re.MULTILINE)
    offenders = [p.name for p in source.rglob("*.py") if imports.search(p.read_text("utf-8"))]
    assert offenders == []
