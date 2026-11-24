import asyncio
import json

import httpx
import pytest
from korpa_api.ai import evaluate, llm
from korpa_api.ai.failover import FailoverExtractor, Provider

RAW = '{"items": []}'


class Clock:
    def __init__(self):
        self.now = 0
        self.waits = []

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def failure(status=429, retry_after="86400", code="rate_limit_exceeded"):
    response = httpx.Response(
        status,
        headers={"retry-after": retry_after},
        json={"error": {"code": code}},
        request=httpx.Request("POST", "https://example.org"),
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as cause:
        error = llm.ModelError(f"HTTP {status} {code}")
        error.__cause__ = cause
        return error


class Model:
    def __init__(self, model, clock, outcomes=()):
        self.model = model
        self.clock = clock
        self.outcomes = list(outcomes)
        self.calls = []

    async def generate_json(self, system, user, schema, timeout=10):
        self.calls.append((user, self.clock()))
        result = self.outcomes.pop(0) if self.outcomes else RAW
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.parametrize("first,second", [("gemini", "groq"), ("groq", "gemini")])
@pytest.mark.parametrize("retry_after", ["86400", ""])
def test_daily_quota_switches_same_sentence_and_keeps_exhausted_provider_idle(
    first, second, retry_after
):
    clock = Clock()
    primary = Model(first + "-model", clock, [failure(retry_after=retry_after, code="daily_quota")])
    alternate = Model(second + "-model", clock)
    interval = 30 if second == "groq" else 6
    pool = FailoverExtractor(
        [Provider(first, primary, 6), Provider(second, alternate, interval)],
        clock=clock,
        sleep=clock.sleep,
    )

    async def run():
        for sentence in ("mleko", "hleb", "jaja"):
            assert await pool.extract_raw(sentence) == RAW
            assert (pool.provider, pool.model) == (second, second + "-model")

    asyncio.run(run())
    assert [sentence for sentence, _ in primary.calls] == ["mleko"]
    assert [sentence for sentence, _ in alternate.calls] == ["mleko", "hleb", "jaja"]
    assert [when for _, when in alternate.calls] == [6, 6 + interval, 6 + 2 * interval]


@pytest.mark.parametrize(
    "error",
    [
        failure(503, "30"),
        failure(500, "30"),
        failure(400, "30", "json_validate_failed"),
        llm.ModelError("empty answer"),
        llm.ModelError("incomplete answer (finishReason=length)"),
    ],
)
def test_temporary_or_invalid_generation_uses_other_provider(error):
    clock = Clock()
    first = Model("gemini-model", clock, [error])
    second = Model("groq-model", clock)
    pool = FailoverExtractor(
        [Provider("gemini", first, 6), Provider("groq", second, 30)], clock=clock, sleep=clock.sleep
    )
    assert asyncio.run(pool.extract_raw("mleko")) == RAW
    assert len(first.calls) == len(second.calls) == 1


def test_invalid_json_fails_over_before_recording():
    clock = Clock()
    first = Model("gemini-model", clock, ["not JSON"])
    second = Model("groq-model", clock)
    pool = FailoverExtractor(
        [Provider("gemini", first, 6), Provider("groq", second, 30)], clock=clock, sleep=clock.sleep
    )
    assert asyncio.run(pool.extract_raw("mleko")) == RAW
    assert len(second.calls) == 1


@pytest.mark.parametrize(
    "error",
    [
        failure(400, "1", "invalid_schema"),
        failure(401),
        failure(403),
        failure(404),
        llm.ModelError("model refused the request"),
    ],
)
def test_configuration_auth_and_refusal_errors_do_not_trigger_failover(error):
    clock = Clock()
    first = Model("gemini-model", clock, [error])
    second = Model("groq-model", clock)
    pool = FailoverExtractor(
        [Provider("gemini", first, 6), Provider("groq", second, 30)], clock=clock, sleep=clock.sleep
    )
    with pytest.raises(llm.ModelError):
        asyncio.run(pool.extract_raw("mleko"))
    assert second.calls == []


def test_both_temporarily_limited_waits_for_first_reset_and_recovers():
    clock = Clock()
    first = Model("gemini-model", clock, [failure(retry_after="60")])
    second = Model("groq-model", clock, [failure(retry_after="90")])
    pool = FailoverExtractor(
        [Provider("gemini", first, 6), Provider("groq", second, 30)], clock=clock, sleep=clock.sleep
    )
    assert asyncio.run(pool.extract_raw("mleko")) == RAW
    assert [when for _, when in first.calls] == [0, 60]
    assert clock.waits == [6, 54]


def test_both_daily_quotas_stop_without_waiting_all_day():
    clock = Clock()
    first = Model("gemini-model", clock, [failure()])
    second = Model("groq-model", clock, [failure()])
    pool = FailoverExtractor(
        [Provider("gemini", first, 6), Provider("groq", second, 30)], clock=clock, sleep=clock.sleep
    )
    with pytest.raises(llm.ModelError, match="Both providers are rate-limited"):
        asyncio.run(pool.extract_raw("mleko"))
    assert len(first.calls) == len(second.calls) == 1
    assert sum(clock.waits) == 6


def test_auto_configuration_requires_both_keys_and_keeps_provider_state(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("LLM_API_KEY", "gemini-test-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-model")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert llm.configured_model() is None
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("GROQ_MODEL", "")
    first = llm.configured_model()
    assert isinstance(first, FailoverExtractor)
    assert first is llm.configured_model()
    assert [p.name for p in first.providers] == ["gemini", "groq"]


def test_live_and_replay_record_the_actual_provider_and_model(tmp_path, monkeypatch):
    from test_ai_eval import write_inputs

    labels, _ = write_inputs(tmp_path)
    clock = Clock()
    first = Model("gemini-model", clock, [RAW, failure()])
    second = Model("groq-model", clock)
    pool = FailoverExtractor(
        [Provider("gemini", first, 6), Provider("groq", second, 30)], clock=clock, sleep=clock.sleep
    )
    monkeypatch.setattr(evaluate, "configured_extractor", lambda: pool)
    monkeypatch.setattr(evaluate.asyncio, "sleep", clock.sleep)
    recorded, report, replay = (
        tmp_path / filename for filename in ("live.jsonl", "out.md", "replay.md")
    )
    assert (
        evaluate.main(
            ["--live", "--phrases", str(labels), "--record", str(recorded), "--out", str(report)]
        )
        == 0
    )
    rows = [json.loads(line) for line in recorded.read_text(encoding="utf-8").splitlines()]
    assert [row["provider"] for row in rows] == ["gemini", "groq", "groq"]
    assert [row["model"] for row in rows] == ["gemini-model", "groq-model", "groq-model"]
    assert [row["id"] for row in rows] == [1, 2, 3]
    assert (
        evaluate.main(["--recorded", str(recorded), "--phrases", str(labels), "--out", str(replay)])
        == 0
    )
    for path in (report, replay):
        text = path.read_text(encoding="utf-8")
        assert "Providers: gemini, groq" in text and "Mixed-provider failover run" in text
        assert "gemini-model, groq-model" in text


def test_concurrent_requests_keep_their_own_provider_provenance():
    clock = Clock()
    first = Model("gemini-model", clock, [RAW, failure()])
    second = Model("groq-model", clock)
    pool = FailoverExtractor(
        [Provider("gemini", first, 6), Provider("groq", second, 30)], clock=clock, sleep=clock.sleep
    )

    async def run():
        ready, done = asyncio.Event(), asyncio.Event()

        async def request_one():
            await pool.extract_raw("mleko")
            ready.set()
            await done.wait()
            return pool.provider, pool.model

        async def request_two():
            await ready.wait()
            await pool.extract_raw("hleb")
            done.set()
            return pool.provider, pool.model

        return await asyncio.gather(request_one(), request_two())

    assert asyncio.run(run()) == [("gemini", "gemini-model"), ("groq", "groq-model")]


def test_repeated_outages_have_a_bounded_attempt_count():
    clock = Clock()
    first = Model("gemini-model", clock, [failure(503, "6") for _ in range(5)])
    second = Model("groq-model", clock, [failure(503, "6") for _ in range(5)])
    pool = FailoverExtractor(
        [Provider("gemini", first, 6), Provider("groq", second, 30)], clock=clock, sleep=clock.sleep
    )
    with pytest.raises(llm.ModelError, match="bounded failover"):
        asyncio.run(pool.extract_raw("mleko"))
    assert len(first.calls) + len(second.calls) == 4
