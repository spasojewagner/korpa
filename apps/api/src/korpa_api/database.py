from collections.abc import AsyncIterator

import sqlalchemy as sa
from fastapi import Request
from korpa_ingest.db import database_url
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession


def async_database_url() -> str:
    """The same database for asyncpg, which knows neither libpq's sslmode nor channel_binding.

    Hosted URLs (e.g. Neon) carry ?sslmode=require&channel_binding=require;
    asyncpg takes ssl=<mode> instead.
    """
    url = make_url(database_url())
    query = dict(url.query)
    query.pop("channel_binding", None)
    sslmode = query.pop("sslmode", None)
    if isinstance(sslmode, str) and sslmode != "disable":
        query["ssl"] = sslmode
    url = url.set(drivername="postgresql+asyncpg", query=query)
    return url.render_as_string(hide_password=False)


async def session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessions() as instance:
        # Read transactions also make date/trigram configuration request-local.
        async with instance.begin():
            await instance.execute(sa.text("SET TRANSACTION READ ONLY"))
            yield instance
