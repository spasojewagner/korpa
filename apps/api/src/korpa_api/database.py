from collections.abc import AsyncIterator

import sqlalchemy as sa
from fastapi import Request
from korpa_ingest.db import database_url
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession


def async_database_url() -> str:
    return (
        make_url(database_url())
        .set(drivername="postgresql+asyncpg")
        .render_as_string(
            hide_password=False,
        )
    )


async def session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessions() as instance:
        # Read transactions also make date/trigram configuration request-local.
        async with instance.begin():
            await instance.execute(sa.text("SET TRANSACTION READ ONLY"))
            yield instance
