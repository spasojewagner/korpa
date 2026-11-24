"""Sequential provider failover with independent cooldowns and explicit provenance."""

import asyncio
import json
import logging
import math
import re
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass

import httpx

from korpa_api.ai.llm import (
    PROMPT,
    SCHEMA,
    Extraction,
    Extractor,
    ModelError,
    parse_extraction,
)


def recoverable(error: ModelError) -> bool:
    cause = error.__cause__
    if isinstance(cause, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(cause, httpx.HTTPStatusError):
        if cause.response.status_code in {429, 500, 502, 503, 504}:
            return True
        try:
            return (
                cause.response.status_code == 400
                and cause.response.json()["error"]["code"] == "json_validate_failed"
            )
        except (ValueError, KeyError, TypeError):
            return False
    # Refusals and configuration errors are not grounds for trying a different model.
    return str(error) in {
        "invalid JSON",
        "unexpected shape",
        "empty answer",
        "no text in the answer",
    } or "finishReason=length" in str(error)


def cooldown(error: ModelError) -> float:
    cause = error.__cause__
    if not isinstance(cause, httpx.HTTPStatusError):
        return 30
    response = cause.response
    try:
        value = float(response.headers.get("retry-after", ""))
        if math.isfinite(value) and value > 0:
            return max(6, value)
    except ValueError:
        pass
    # A daily quota is different from a short request/token burst. Keep using the
    # other provider rather than repeatedly trying an exhausted daily allowance.
    if response.status_code == 429:
        if re.search(r"per.?day|daily|\brpd\b|\btpd\b", response.text, re.IGNORECASE):
            return 86400
        return 60
    return 30


@dataclass
class Provider:
    name: str
    extractor: Extractor
    interval: float
    next_call: float = 0


class FailoverExtractor:
    def __init__(
        self,
        providers: list[Provider],
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.providers = providers
        self.clock = clock
        self.sleep = sleep
        self.active = 0
        self.last_call: float | None = None
        self.lock = asyncio.Lock()
        self.source: ContextVar[tuple[str, str]] = ContextVar(
            "model_source", default=(providers[0].name, providers[0].extractor.model)
        )

    @property
    def model(self) -> str:
        return self.source.get()[1]

    @property
    def provider(self) -> str:
        return self.source.get()[0]

    async def extract(self, sentence: str) -> Extraction:
        return parse_extraction(await self.extract_raw(sentence))

    async def extract_raw(self, sentence: str) -> str:
        return await self._generate(PROMPT, sentence, SCHEMA, 10, extraction=True)

    async def generate_json(
        self, system: str, user: str, schema: dict[str, object], timeout: float = 10
    ) -> str:
        return await self._generate(system, user, schema, timeout, extraction=False)

    async def _generate(
        self,
        system: str,
        user: str,
        schema: dict[str, object],
        timeout: float,
        *,
        extraction: bool,
    ) -> str:
        async with self.lock:
            deadline = self.clock() + 300
            last_error: ModelError | None = None
            for _ in range(4):
                order = [
                    (self.active + offset) % len(self.providers)
                    for offset in range(len(self.providers))
                ]
                now = self.clock()
                ready = [index for index in order if self.providers[index].next_call <= now]
                index = ready[0] if ready else min(order, key=lambda n: self.providers[n].next_call)
                entry = self.providers[index]
                due = max(
                    entry.next_call, (self.last_call + 6) if self.last_call is not None else now
                )
                if due > deadline:
                    raise ModelError(
                        "Both providers are rate-limited; completed recordings are "
                        "retained. Retry after a provider's quota resets."
                    ) from last_error
                if due > now:
                    await self.sleep(due - now)
                self.last_call = self.clock()
                entry.next_call = self.last_call + entry.interval
                try:
                    text = await entry.extractor.generate_json(system, user, schema, timeout)
                    if extraction:
                        parse_extraction(text)
                    else:
                        try:
                            json.loads(text)
                        except ValueError as error:
                            raise ModelError("invalid JSON") from error
                except ModelError as error:
                    if not recoverable(error):
                        raise
                    last_error = error
                    entry.next_call = max(entry.next_call, self.clock() + cooldown(error))
                    self.active = (index + 1) % len(self.providers)
                    # Provider diagnostics are already sanitized; never log raw outputs or keys.
                    logging.getLogger(__name__).warning(
                        "%s unavailable: %s; trying alternate provider", entry.name, error
                    )
                    continue
                self.active = index
                self.source.set((entry.name, entry.extractor.model))
                return text
            raise ModelError(
                f"Both providers failed after bounded failover attempts: {last_error}"
            ) from last_error
