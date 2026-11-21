from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from korpa_api import analytics, repository
from korpa_api.database import session
from korpa_api.pricing import belgrade_today
from korpa_api.schemas import (
    BasketRequest,
    BasketResponse,
    CategoryItem,
    IndexResponse,
    QualityResponse,
    SearchParams,
    SearchResponse,
)

router = APIRouter(prefix="/api")
Database = Annotated[AsyncSession, Depends(session)]


@router.get("/search", response_model=SearchResponse)
async def search(params: Annotated[SearchParams, Query()], database: Database) -> SearchResponse:
    """Search current-priced products by text and/or category.

    At least one of q or category is required. With category alone, order by number of
    current retail formats descending, then name; barcode breaks ties for stable pagination.
    Text queries retain relevance ranking, optionally filtered by category.
    """
    return await repository.search(database, params, belgrade_today())


@router.post("/basket", response_model=BasketResponse)
async def basket(body: BasketRequest, database: Database) -> BasketResponse:
    return await repository.basket(database, body, belgrade_today())


@router.get("/categories", response_model=list[CategoryItem])
async def categories(database: Database) -> list[CategoryItem]:
    return await repository.categories(database)


@router.get("/quality", response_model=QualityResponse)
async def quality(database: Database) -> QualityResponse:
    return await repository.quality(database, belgrade_today())


@router.get("/index", response_model=IndexResponse)
async def price_index(database: Database) -> IndexResponse:
    return await analytics.price_index(database, belgrade_today())
