import json
import logging
import os
from datetime import UTC, datetime
from typing import Annotated

import httpx
import typer
from dotenv import load_dotenv
from sqlalchemy import create_engine

from korpa_ingest.compat import PROFILE
from korpa_ingest.db import database_url
from korpa_ingest.normalize import normalize
from korpa_ingest.portal import Download, PortalClient
from korpa_ingest.reader import Parsed, Report, read_csv
from korpa_ingest.store import StorageLimitError, compact_monthly, persist, validators

app = typer.Typer(no_args_is_help=True)


@app.command()
def ingest(
    retailer: Annotated[str | None, typer.Option(help="Publisher slug from the portal")] = None,
    all_retailers: Annotated[
        bool, typer.Option("--all", help="Import all discovered retailers")
    ] = False,
    dry_run: Annotated[bool, typer.Option(help="Validate without connecting to the DB")] = False,
    report_row_errors: Annotated[
        bool,
        typer.Option(
            "--report-row-errors",
            help="Exit 0 when the only problems are invalid rows (still counted and reported)",
        ),
    ] = False,
) -> None:
    """Discover price lists, validate them, and report every rejected row."""
    if bool(retailer) == all_retailers:
        raise typer.BadParameter("Choose exactly one of --retailer <slug> or --all")
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    engine = None if dry_run else create_engine(database_url())
    failed = False
    try:
        with httpx.Client(
            timeout=60,
            follow_redirects=True,
            headers={
                "User-Agent": "Korpa/0.1 (+https://github.com/spasojewagner/korpa)",
            },
        ) as client:
            portal = PortalClient(client, os.getenv("PORTAL_BASE_URL") or "https://data.gov.rs")
            sources = portal.discover()
            issues = {
                slug: reason
                for slug, reason in portal.issues.items()
                if all_retailers or slug == retailer
            }
            if issues:
                typer.echo(json.dumps({"discovery_errors": issues}, ensure_ascii=False))
                failed = True
            selected = [s for s in sources if all_retailers or s.slug == retailer]
            if retailer and not selected:
                raise typer.BadParameter(
                    "No unambiguous consolidated CSV for slug. Available: "
                    + ", ".join(source.slug for source in sources)
                )
            if not selected:
                raise typer.BadParameter("No consolidated CSV resources discovered")
            for source in selected:
                started_at = datetime.now(UTC)
                download = Download(0, b"")
                try:
                    etag, modified = (
                        validators(engine, source) if engine is not None else (None, None)
                    )
                    download = portal.download(source, etag, modified)
                    parsed = (
                        normalize(read_csv(download.content, profile=PROFILE))
                        if download.status != 304
                        else (Parsed([], Report(profile=PROFILE)))
                    )
                except (httpx.HTTPError, ValueError) as exc:
                    report = Report(profile=PROFILE)
                    report.error("download")
                    if isinstance(exc, httpx.HTTPStatusError):
                        download = Download(exc.response.status_code, b"")
                    parsed = Parsed([], report)
                    logging.error("Download failed for %s: %s", source.slug, type(exc).__name__)
                if engine is not None:
                    persist(engine, source, parsed, download, started_at)
                typer.echo(
                    json.dumps(
                        {
                            "retailer": source.slug,
                            "dataset_id": source.dataset_id,
                            "source_url": source.url,
                            "license": source.license,
                            "http_status": download.status,
                            "dry_run": dry_run,
                            **parsed.report.as_dict(),
                        },
                        ensure_ascii=False,
                    )
                )
                failed |= bool(parsed.report.errors)
        if engine is not None:
            compact_monthly(engine, datetime.now(UTC).date())
    except StorageLimitError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
    finally:
        if engine is not None:
            engine.dispose()
    if failed and not report_row_errors:
        raise typer.Exit(1)


@app.callback()
def main() -> None:
    """Korpa data tools."""
