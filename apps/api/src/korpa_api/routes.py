from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from korpa_api import repository
from korpa_api.database import session
from korpa_api.pricing import belgrade_today
from korpa_api.schemas import (
    BasketRequest,
    BasketResponse,
    CategoryItem,
    QualityResponse,
    SearchParams,
    SearchResponse,
)

router = APIRouter(prefix="/api")
Database = Annotated[AsyncSession, Depends(session)]


@router.get("/search", response_model=SearchResponse)
async def search(params: Annotated[SearchParams, Query()], database: Database) -> SearchResponse:
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
