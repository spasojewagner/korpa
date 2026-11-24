import asyncio
import json
from copy import deepcopy

import httpx
import pytest
from korpa_api.ai import evaluate, llm, notes

RAW = json.dumps(
    {
        "items": [{"phrase": "2 mleka", "query": "mleko", "qty": 2, "proposed": False}],
        "budget_rsd": None,
        "people": None,
    }
)


def answer(text=RAW, finish="stop"):
    return {"choices": [{"message": {"content": text}, "finish_reason": finish}]}


def test_groq_request_and_shared_extraction_parser():
    schema_before = deepcopy(llm.SCHEMA)

    def handler(request):
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        assert "x-goog-api-key" not in request.headers
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-oss-20b"
        assert body["messages"] == [
            {"role": "system", "content": llm.PROMPT},
            {"role": "user", "content": "2 mleka"},
        ]
        response_format = body["response_format"]
        assert response_format["type"] == "json_schema"
        assert response_format["json_schema"]["strict"] is True
        schema = response_format["json_schema"]["schema"]
        assert schema["required"] == ["items", "budget_rsd", "people"]
        assert schema["additionalProperties"] is False
        assert schema["properties"]["items"]["items"]["additionalProperties"] is False
        assert schema["properties"]["budget_rsd"]["anyOf"][1] == {"type": "null"}
        return httpx.Response(200, json=answer())

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await llm.GroqExtractor("test-key", "openai/gpt-oss-20b", client).extract(
                "2 mleka"
            )

    extraction = asyncio.run(run())
    assert extraction.items[0].query == "mleko" and extraction.items[0].qty == 2
    assert extraction.budget_para is None
    assert llm.SCHEMA == schema_before


def test_groq_uses_same_checked_notes_contract():
    raw = '{"notes": []}'

    def handler(request):
        schema = json.loads(request.content)["response_format"]["json_schema"]["schema"]
        assert schema["properties"]["notes"]["items"]["additionalProperties"] is False
        assert schema["properties"]["notes"]["items"]["required"] == ["text", "codes"]
        return httpx.Response(200, json=answer(raw))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model = llm.GroqExtractor("test-key", "openai/gpt-oss-20b", client)
            return await model.generate_json(notes.PROMPT, "facts", notes.SCHEMA)

    assert asyncio.run(run()) == raw


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"choices": []},
        answer(""),
        answer(None),
        answer([], "stop"),
        answer("{}", "length"),
        {"choices": [{"message": {"content": "{}", "refusal": "no"}, "finish_reason": "stop"}]},
    ],
)
def test_groq_rejects_missing_truncated_or_refused_output(payload):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ) as client:
            await llm.GroqExtractor("key", "model", client).extract_raw("mleko")

    with pytest.raises(llm.ModelError):
        asyncio.run(run())


def test_groq_http_error_keeps_status_retry_headers_and_masks_keys():
    key = "gsk_abcdefghijklmnopqrstuvwxyz123456"
    echoed = "gsk_987654321abcdefghijklmnopqrstuvwxyz"

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    429,
                    headers={"retry-after": "45"},
                    json={
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": f"wait; {key}; {echoed}",
                        }
                    },
                )
            )
        ) as client:
            await llm.GroqExtractor(key, "model", client).extract_raw("mleko")

    with pytest.raises(llm.ModelError) as error:
        asyncio.run(run())
    assert str(error.value).startswith("HTTP 429 rate_limit_exceeded:")
    assert key not in str(error.value) and echoed not in str(error.value)
    assert isinstance(error.value.__cause__, httpx.HTTPStatusError)
    assert error.value.__cause__.response.headers["retry-after"] == "45"


@pytest.mark.parametrize(
    "provider,kind", [("gemini", llm.GeminiExtractor), ("groq", llm.GroqExtractor)]
)
def test_configuration_selects_provider_explicitly(monkeypatch, provider, kind):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    assert isinstance(llm.configured_extractor(), kind)
    assert isinstance(llm.configured_model(), kind)
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    assert llm.configured_model() is None


def test_groq_live_evaluation_defaults_to_free_plan_pacing_and_replays(tmp_path, monkeypatch):
    from test_ai_eval import write_inputs

    labels, _ = write_inputs(tmp_path)
    waits = []
    original = evaluate.run

    async def sleep(delay):
        waits.append(delay)

    async def run(args):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=answer()))
        ) as client:
            monkeypatch.setattr(
                evaluate,
                "configured_extractor",
                lambda: llm.GroqExtractor("test-key", "openai/gpt-oss-20b", client),
            )
            await original(args)

    monkeypatch.setattr(evaluate, "run", run)
    monkeypatch.setattr(evaluate.asyncio, "sleep", sleep)
    recorded = tmp_path / "live.jsonl"
    report = tmp_path / "report.md"
    assert (
        evaluate.main(
            ["--live", "--phrases", str(labels), "--record", str(recorded), "--out", str(report)]
        )
        == 0
    )
    assert waits == [30, 30]
    assert "Model: openai/gpt-oss-20b" in report.read_text(encoding="utf-8")
    assert (
        evaluate.main(
            [
                "--recorded",
                str(recorded),
                "--phrases",
                str(labels),
                "--out",
                str(tmp_path / "replayed.md"),
            ]
        )
        == 0
    )


@pytest.mark.parametrize(
    "header,delay", [("45", 45), ("1.5", 6), ("invalid", 6), ("-5", 6), ("nan", 6), ("inf", 6)]
)
def test_evaluation_honors_retry_after_without_reducing_backoff(monkeypatch, header, delay):
    calls = []
    waits = []

    class Model:
        async def extract_raw(self, sentence):
            calls.append(sentence)
            if len(calls) == 1:
                response = httpx.Response(
                    429,
                    headers={"retry-after": header},
                    request=httpx.Request("POST", "https://api.groq.com"),
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    raise llm.ModelError("HTTP 429 rate_limit_exceeded") from error
            return RAW

    async def sleep(value):
        waits.append(value)

    monkeypatch.setattr(evaluate.asyncio, "sleep", sleep)
    result = asyncio.run(
        evaluate.extract_with_retry(Model(), evaluate.Phrase(id=1, sentence="mleko", expected=[]))
    )
    assert result == RAW and len(calls) == 2 and waits == [delay]


def test_daily_quota_long_wait_stops_with_clear_message(monkeypatch):
    async def sleep(value):
        pytest.fail("do not retry before a long quota reset")

    class Model:
        async def extract_raw(self, sentence):
            response = httpx.Response(
                429,
                headers={"retry-after": "86400"},
                request=httpx.Request("POST", "https://api.groq.com"),
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise llm.ModelError("HTTP 429 daily quota") from error

    monkeypatch.setattr(evaluate.asyncio, "sleep", sleep)
    with pytest.raises(evaluate.EvaluationError, match="quota resets"):
        asyncio.run(
            evaluate.extract_with_retry(
                Model(), evaluate.Phrase(id=1, sentence="mleko", expected=[])
            )
        )


@pytest.mark.parametrize("interval", ["0", "5", "61"])
def test_evaluation_rejects_unsafe_call_intervals(interval):
    with pytest.raises(SystemExit) as error:
        evaluate.main(["--interval-seconds", interval])
    assert error.value.code == 2
