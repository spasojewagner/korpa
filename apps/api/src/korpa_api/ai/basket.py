"""Basket from a sentence: model extraction, then the regular product search for each item."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from korpa_api import repository
from korpa_api.ai.llm import Extractor
from korpa_api.schemas import AiBasketItem, AiBasketResponse, SearchParams

CANDIDATES = 5


async def ai_basket(
    session: AsyncSession, sentence: str, extractor: Extractor, as_of: date
) -> AiBasketResponse:
    extraction = await extractor.extract(sentence)
    items = []
    for item in extraction.items:
        found = await repository.search(
            session, SearchParams(q=item.query, limit=CANDIDATES), as_of
        )
        items.append(
            AiBasketItem(phrase=item.phrase, query=item.query, qty=item.qty, candidates=found.items)
        )
    return AiBasketResponse(as_of=as_of, model=extractor.model, items=items)
