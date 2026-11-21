"""Read-only MCP tools backed by the same reads as REST and the product graph."""

from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import FastAPI
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.types import Receive, Scope, Send

from korpa_api import repository
from korpa_api.database import session
from korpa_api.gql.context import Context
from korpa_api.pricing import belgrade_today
from korpa_api.schemas import (
    Barcode,
    BasketItem,
    BasketRequest,
    BasketResponse,
    SearchParams,
    SearchResponse,
)

SOURCE = (
    "Prices come from the retailers' open-data price lists on data.gov.rs. "
    "Amounts are in para (1/100 RSD). Korpa is not a state service."
)
read_session = asynccontextmanager(session)
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)


class ProductPrice(BaseModel):
    format_id: int
    format_name: str
    retailer_name: str
    retailer_slug: str
    regular_para: int
    discounted_para: int | None
    effective_para: int
    unit_price_para: int
    vat: int
    discount_from: date | None
    discount_to: date | None
    list_date: date
    as_of: date


class PricesResponse(BaseModel):
    prices: list[ProductPrice]
    as_of: date


def create_server(app: FastAPI) -> tuple[MCPServer[None], Starlette]:
    """Create a fresh SDK session manager for each host-app lifespan."""
    server: MCPServer[None] = MCPServer("Korpa", instructions=SOURCE)
    request = Request({"type": "http", "app": app})

    @server.tool(description="Search current-priced products. " + SOURCE, annotations=READ_ONLY)
    async def search_products(
        query: Annotated[str, Field(min_length=2, max_length=100, strict=True)],
        category: Annotated[int | None, Field(ge=1, le=25, strict=True)] = None,
        limit: Annotated[int, Field(ge=1, le=20, strict=True)] = 10,
    ) -> SearchResponse:
        params = SearchParams(q=query, category=category, limit=limit)
        as_of = belgrade_today()
        async with read_session(request) as database:
            return await repository.search(database, params, as_of)

    @server.tool(
        description="Compare current prices by retail format; unknown barcodes have no prices. "
        + SOURCE,
        annotations=READ_ONLY,
    )
    async def compare_prices(barcode: Barcode) -> PricesResponse:
        as_of = belgrade_today()
        prices: list[ProductPrice] = []
        async with read_session(request) as database:
            loaders = Context(database, as_of)
            rows = await loaders.prices.load(barcode)
            formats = await loaders.formats.load_many([row["format_id"] for row in rows])
            retailers = await loaders.retailers.load_many([row["retailer_id"] for row in formats])
            for row, retail_format, retailer in zip(rows, formats, retailers, strict=True):
                prices.append(
                    ProductPrice(
                        format_id=row["format_id"],
                        format_name=retail_format["name"],
                        retailer_name=retailer["name"],
                        retailer_slug=retailer["slug"],
                        regular_para=row["regular"],
                        discounted_para=row["discounted"],
                        effective_para=row["effective_para"],
                        unit_price_para=row["unit_price"],
                        vat=row["vat"],
                        discount_from=row["disc_from"],
                        discount_to=row["disc_to"],
                        list_date=row["list_date"],
                        as_of=as_of,
                    )
                )
        return PricesResponse(prices=prices, as_of=as_of)

    @server.tool(
        description="Rank retail formats by basket total, including missing barcodes. " + SOURCE,
        annotations=READ_ONLY,
    )
    async def cheapest_basket(
        items: Annotated[list[BasketItem], Field(min_length=1, max_length=50)],
    ) -> BasketResponse:
        body = BasketRequest(items=items)
        as_of = belgrade_today()
        async with read_session(request) as database:
            return await repository.basket(database, body, as_of)

    transport = server.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                "korpa-api.onrender.com",
                "korpa-api.onrender.com:*",
                "localhost",
                "localhost:*",
                "127.0.0.1",
                "127.0.0.1:*",
                "[::1]",
                "[::1]:*",
            ],
            allowed_origins=[
                "https://korpa-api.onrender.com",
                "https://ai-korpa.vercel.app",
                "http://localhost:*",
                "http://127.0.0.1:*",
                "http://[::1]:*",
            ],
        ),
    )
    return server, transport


async def endpoint(scope: Scope, receive: Receive, send: Send) -> None:
    """Forward to the transport owned by this host app's active lifespan."""
    transport: Starlette = scope["app"].state.mcp_transport
    await transport(scope, receive, send)
