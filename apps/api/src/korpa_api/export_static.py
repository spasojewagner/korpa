"""Write the static JSON the web app reads before it calls the API.

Run nightly after ingest: `python -m korpa_api.export_static --out apps/web/public/data`.
The files have exactly the shape of GET /api/categories and GET /api/quality.
"""

import argparse
import asyncio
import json
from pathlib import Path

import sqlalchemy as sa
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from korpa_api import repository
from korpa_api.database import async_database_url
from korpa_api.pricing import belgrade_today
from korpa_api.schemas import CategoryItem


async def export(out: Path) -> list[Path]:
    engine = create_async_engine(async_database_url())
    try:
        async with AsyncSession(engine) as session, session.begin():
            await session.execute(sa.text("SET TRANSACTION READ ONLY"))
            categories = await repository.categories(session)
            quality = await repository.quality(session, belgrade_today())
    finally:
        await engine.dispose()
    payloads = {
        "categories.json": TypeAdapter(list[CategoryItem]).dump_python(categories, mode="json"),
        "quality.json": quality.model_dump(mode="json"),
    }
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, payload in payloads.items():
        path = out / name
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), "utf-8")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("apps/web/public/data"))
    for path in asyncio.run(export(parser.parse_args().out)):
        print(path)


if __name__ == "__main__":
    main()
