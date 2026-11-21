from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from korpa_api import analytics, repository
from korpa_api.ai.basket import ai_basket
from korpa_api.ai.limits import RateLimiter
from korpa_api.ai.llm import Extractor, ModelError, configured_extractor
from korpa_api.database import session
from korpa_api.pricing import belgrade_today
from korpa_api.schemas import (
    AiBasketRequest,
    AiBasketResponse,
    AiStatus,
    BasketRequest,
    BasketResponse,
    CategoryItem,
    IndexResponse,
    QualityResponse,
    SearchParams,
    SearchResponse,
    SignalsParams,
    SignalsResponse,
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


@router.get("/signals", response_model=SignalsResponse)
async def signals(params: Annotated[SignalsParams, Query()], database: Database) -> SignalsResponse:
    return await analytics.signals(database, params, belgrade_today())


ai_limits = RateLimiter()
AiExtractor = Annotated[Extractor | None, Depends(configured_extractor)]


@router.get("/ai/status", response_model=AiStatus)
async def ai_status(extractor: AiExtractor) -> AiStatus:
    return AiStatus(enabled=extractor is not None)


@router.post("/ai/basket", response_model=AiBasketResponse)
async def basket_from_sentence(
    body: AiBasketRequest, request: Request, database: Database, extractor: AiExtractor
) -> AiBasketResponse:
    """Turn a sentence into basket items; the model only proposes search queries and quantities."""
    if extractor is None:
        raise HTTPException(503, "AI is not configured")
    wait = ai_limits.check(request.client.host if request.client else "unknown")
    if wait is not None:
        raise HTTPException(429, "Too many AI requests", headers={"Retry-After": str(wait)})
    try:
        return await ai_basket(database, body.sentence, extractor, belgrade_today())
    except ModelError as exc:
        raise HTTPException(503, "The AI model is unavailable") from exc
