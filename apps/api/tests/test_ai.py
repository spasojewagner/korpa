import json
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from korpa_api import routes
from korpa_api.ai import basket
from korpa_api.ai.basket import ExtractionCache
from korpa_api.ai.limits import RateLimiter
from korpa_api.ai.llm import (
    Extraction,
    GeminiExtractor,
    ModelError,
    configured_extractor,
    parse_extraction,
)
from korpa_api.main import app
from test_rest import AS_OF, B1
from test_rest import client as client
from test_rest import engine as engine


class FakeExtractor:
    model = "fake-model"

    def __init__(self, text: str) -> None:
        self.text = text

    async def extract(self, sentence: str) -> Extraction:
        return parse_extraction(self.text)


class FailingExtractor:
    model = "fake-model"

    async def extract(self, sentence: str) -> Extraction:
        raise ModelError("timeout")


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes, "ai_limits", RateLimiter())
    monkeypatch.setattr(basket, "cache", ExtractionCache())
    monkeypatch.setattr(routes, "belgrade_today", lambda: AS_OF)
    yield
    app.dependency_overrides.clear()


def test_parse_validates_merges_and_caps() -> None:
    raw = {
        "items": [
            {"phrase": "mleko", "query": "  Mleko ", "qty": 2},
            {"phrase": "opet mleko", "query": "mleko", "qty": 1},
            {"phrase": "cena", "query": "x", "qty": 1},
            {"phrase": "loše", "query": "hleb", "qty": 0},
            {"phrase": "višak", "query": "jaja", "qty": 3, "price": 1},
        ]
        + [{"phrase": f"p{i}", "query": f"proizvod {i}", "qty": 1} for i in range(30)]
    }
    items = parse_extraction(json.dumps(raw)).items
    assert [(i.query, i.qty) for i in items[:2]] == [("mleko", 2), ("jaja", 3)]
    assert len(items) == 20
    with pytest.raises(ModelError):
        parse_extraction("not json")
    with pytest.raises(ModelError):
        parse_extraction('["items"]')


def test_gemini_request_shape_and_errors() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers["x-goog-api-key"]
        seen["body"] = json.loads(request.content)
        text = json.dumps({"items": [{"phrase": "10 jaja", "query": "jaja", "qty": 10}]})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    async def run(transport: httpx.MockTransport) -> Extraction:
        async with httpx.AsyncClient(transport=transport) as http:
            return await GeminiExtractor("secret", "model-x", http).extract("10 jaja")

    import asyncio

    result = asyncio.run(run(httpx.MockTransport(handler)))
    assert [(i.query, i.qty) for i in result.items] == [("jaja", 10)]
    assert str(seen["url"]).endswith("/models/model-x:generateContent")
    assert seen["key"] == "secret"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["generationConfig"]["responseFormat"]["text"]["mimeType"] == "APPLICATION_JSON"
    assert body["contents"][0]["parts"][0]["text"] == "10 jaja"
    with pytest.raises(ModelError):
        asyncio.run(run(httpx.MockTransport(lambda r: httpx.Response(500, json={}))))
    with pytest.raises(ModelError):
        asyncio.run(run(httpx.MockTransport(lambda r: httpx.Response(200, json={"x": 1}))))


def test_extractor_requires_full_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    assert configured_extractor() is None
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "k")
    assert configured_extractor() is None
    monkeypatch.setenv("LLM_MODEL", "m")
    extractor = configured_extractor()
    assert extractor is not None and extractor.model == "m"


def test_ai_basket_uses_database_search(client: TestClient) -> None:
    text = json.dumps({"items": [{"phrase": "dva mleka", "query": "mleko", "qty": 2}]})
    app.dependency_overrides[routes.configured_extractor] = lambda: FakeExtractor(text)
    assert client.get("/api/ai/status").json() == {"enabled": True}
    response = client.post("/api/ai/basket", json={"sentence": "dva mleka"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["model"] == "fake-model" and body["as_of"] == AS_OF.isoformat()
    item = body["items"][0]
    assert (item["phrase"], item["query"], item["qty"]) == ("dva mleka", "mleko", 2)
    assert item["candidates"][0]["barcode"] == B1


def test_ai_disabled_failing_and_limited(client: TestClient) -> None:
    app.dependency_overrides[routes.configured_extractor] = lambda: None
    assert client.get("/api/ai/status").json() == {"enabled": False}
    disabled = client.post("/api/ai/basket", json={"sentence": "mleko"})
    assert disabled.status_code == 503
    assert disabled.headers["content-type"].startswith("application/problem+json")
    app.dependency_overrides[routes.configured_extractor] = lambda: FailingExtractor()
    assert client.post("/api/ai/basket", json={"sentence": "mleko"}).status_code == 503
    assert client.post("/api/ai/basket", json={"sentence": "ml"}).status_code == 422
    limited = None
    for _ in range(12):
        limited = client.post("/api/ai/basket", json={"sentence": "mleko"})
    assert limited is not None and limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0


def test_rate_limiter_windows() -> None:
    limiter = RateLimiter(per_minute=2, per_day=3)
    day = date(2026, 11, 22)
    assert limiter.check("a", 0, day) is None
    assert limiter.check("a", 1, day) is None
    assert limiter.check("a", 2, day) == 59
    assert limiter.check("a", 61, day) is None
    assert limiter.check("b", 62, day) == 3600
    assert limiter.check("b", 62, date(2026, 11, 23)) is None


def test_goal_proposals_are_capped_and_budget_is_read() -> None:
    raw = {
        "items": [{"phrase": "hleb", "query": "hleb", "qty": 1, "proposed": False}]
        + [
            {"phrase": f"p{i}", "query": f"sastojak {i}", "qty": 1, "proposed": True}
            for i in range(12)
        ],
        "budget_rsd": 500,
        "people": 4,
    }
    extraction = parse_extraction(json.dumps(raw))
    assert [i.proposed for i in extraction.items].count(True) == 8
    assert extraction.items[0].proposed is False
    assert extraction.budget_para == 50_000
    for bad in (0, -5, 2_000_000, "500", True, 49.5):
        assert parse_extraction(json.dumps({"items": [], "budget_rsd": bad})).budget_para is None


def test_cache_reuses_an_extraction_and_expires() -> None:
    cache = ExtractionCache(size=2, seconds=10)
    first = Extraction(items=[])
    cache.put("m", "Ručak  za ČETVORO", first, now=0)
    assert cache.get("m", "ručak za četvoro", now=5) is first
    assert cache.get("other-model", "ručak za četvoro", now=5) is None
    assert cache.get("m", "ručak za četvoro", now=11) is None
    cache.put("m", "a", first, now=0)
    cache.put("m", "b", first, now=0)
    cache.put("m", "c", first, now=0)
    assert cache.get("m", "a", now=1) is None and cache.get("m", "c", now=1) is first


class CountingExtractor(FakeExtractor):
    calls = 0

    async def extract(self, sentence: str) -> Extraction:
        CountingExtractor.calls += 1
        return await super().extract(sentence)


def test_ai_basket_marks_proposals_returns_budget_and_caches(client: TestClient) -> None:
    text = json.dumps(
        {
            "items": [{"phrase": "mleko", "query": "mleko", "qty": 2, "proposed": True}],
            "budget_rsd": 500,
        }
    )
    extractor = CountingExtractor(text)
    app.dependency_overrides[configured_extractor] = lambda: extractor
    for _ in range(2):
        response = client.post("/api/ai/basket", json={"sentence": "ručak za četvoro do 500 din"})
        assert response.status_code == 200
    body = response.json()
    assert body["budget_para"] == 50_000
    assert body["items"][0]["proposed"] is True
    assert CountingExtractor.calls == 1
