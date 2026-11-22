"""Basket from a sentence: model extraction, then the regular product search for each item."""

import time
from collections import OrderedDict
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from korpa_api import repository
from korpa_api.ai.llm import Extraction, Extractor
from korpa_api.schemas import AiBasketItem, AiBasketResponse, SearchParams

CANDIDATES = 5
CACHE_SIZE = 500
CACHE_SECONDS = 24 * 3600


class ExtractionCache:
    """Same sentence and model within a day: reuse the validated extraction, skip the model call."""

    def __init__(self, size: int = CACHE_SIZE, seconds: float = CACHE_SECONDS) -> None:
        self.size, self.seconds = size, seconds
        self._items: OrderedDict[tuple[str, str], tuple[float, Extraction]] = OrderedDict()

    @staticmethod
    def key(model: str, sentence: str) -> tuple[str, str]:
        return model, " ".join(sentence.lower().split())

    def get(self, model: str, sentence: str, now: float | None = None) -> Extraction | None:
        key = self.key(model, sentence)
        hit = self._items.get(key)
        if hit is None:
            return None
        if (now if now is not None else time.monotonic()) - hit[0] > self.seconds:
            del self._items[key]
            return None
        self._items.move_to_end(key)
        return hit[1]

    def put(self, model: str, sentence: str, value: Extraction, now: float | None = None) -> None:
        key = self.key(model, sentence)
        self._items[key] = (now if now is not None else time.monotonic(), value)
        self._items.move_to_end(key)
        while len(self._items) > self.size:
            self._items.popitem(last=False)


cache = ExtractionCache()


async def ai_basket(
    session: AsyncSession, sentence: str, extractor: Extractor, as_of: date
) -> AiBasketResponse:
    extraction = cache.get(extractor.model, sentence)
    if extraction is None:
        extraction = await extractor.extract(sentence)
        cache.put(extractor.model, sentence, extraction)
    items = []
    for item in extraction.items:
        found = await repository.search(
            session, SearchParams(q=item.query, limit=CANDIDATES), as_of
        )
        items.append(
            AiBasketItem(
                phrase=item.phrase,
                query=item.query,
                qty=item.qty,
                proposed=item.proposed,
                candidates=found.items,
            )
        )
    return AiBasketResponse(
        as_of=as_of, model=extractor.model, items=items, budget_para=extraction.budget_para
    )
