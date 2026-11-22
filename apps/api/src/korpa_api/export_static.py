"""Write the static JSON the web app reads before it calls the API.

Run nightly after ingest: `python -m korpa_api.export_static --out apps/web/public/data`.
The files match GET /api/categories, GET /api/quality, GET /api/index
and GET /api/signals (limit 200).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import sqlalchemy as sa
from korpa_ingest.db import database_url
from pydantic import TypeAdapter
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from korpa_api import analytics, repository
from korpa_api.ai.llm import ModelError, configured_model
from korpa_api.ai.notes import index_notes
from korpa_api.database import async_database_url
from korpa_api.pricing import belgrade_today
from korpa_api.schemas import CategoryItem, IndexResponse, SignalsParams


async def export(out: Path) -> list[Path]:
    as_of = belgrade_today()
    writer = create_engine(database_url())
    try:
        await asyncio.to_thread(analytics.refresh_index, writer, as_of)
    finally:
        writer.dispose()
    engine = create_async_engine(async_database_url())
    try:
        async with AsyncSession(engine) as session, session.begin():
            await session.execute(sa.text("SET TRANSACTION READ ONLY"))
            categories = await repository.categories(session)
            quality = await repository.quality(session, as_of)
            index = await analytics.price_index(session, as_of)
            signals = await analytics.signals(session, SignalsParams(limit=200), as_of)
    finally:
        await engine.dispose()
    payloads = {
        "categories.json": TypeAdapter(list[CategoryItem]).dump_python(categories, mode="json"),
        "quality.json": quality.model_dump(mode="json"),
        "index.json": index.model_dump(mode="json") | await notes(index),
        "signals.json": signals.model_dump(mode="json"),
    }
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, payload in payloads.items():
        path = out / name
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), "utf-8")
        written.append(path)
    return written


async def notes(index: IndexResponse) -> dict[str, object]:
    """Grounded notes for index.json, or nothing when AI is off or the model fails."""
    model = configured_model()
    if model is None:
        return {}
    try:
        kept, proposed = await index_notes(model, index)
    except ModelError as exc:
        print(f"index notes skipped: {exc}", file=sys.stderr)
        return {}
    print(f"index notes: kept {len(kept)} of {proposed}", file=sys.stderr)
    return {"notes": {"model": model.model, "items": kept}} if kept else {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("apps/web/public/data"))
    for path in asyncio.run(export(parser.parse_args().out)):
        print(path)


if __name__ == "__main__":
    main()
