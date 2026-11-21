import json
import subprocess
import sys
from datetime import date

import pytest
from korpa_api.ai import evaluate
from korpa_api.ai.llm import parse_extraction
from test_rest import client as client
from test_rest import engine as engine


def phrase(identifier, expected):
    return evaluate.Phrase(id=identifier, sentence="test", expected=expected)


def expected(terms, qty=1, category=1):
    return {"query_terms": terms, "qty": qty, "category": category}


def items(*pairs):
    return parse_extraction(
        json.dumps({"items": [{"phrase": q, "query": q, "qty": n} for q, n in pairs]})
    ).items


@pytest.mark.parametrize(
    ("terms", "target", "matches"),
    [
        (["ŠEĆER"], "secer beli", True),
        (["mleko"], "МЛЕКО", True),
        (["Ђумбир"], "djumbir", True),
        (["jabuka"], "jabuke", True),
        (["kobasica"], "kobasice", True),
        (["mleko"], "mleka", True),
        (["sir"], "si", False),
        (["čaj", "nana"], "caj nane", False),
        (["hleb", "beli"], "integralni hleb", False),
        (["sir"], "sirće", True),  # The specified rule is substring matching.
    ],
)
def test_matching(terms, target, matches):
    assert evaluate.contains_terms(terms, target) is matches


def test_greedy_one_to_one_in_label_order():
    labels = [
        evaluate.ExpectedItem(**expected(["hleb"])),
        evaluate.ExpectedItem(**expected(["hleb", "beli"])),
    ]
    extracted = items(("beli hleb", 1), ("integralni hleb", 1))
    assert evaluate.match_items(labels, extracted) == [(0, 0)]
    assert evaluate.match_items(labels * 2, extracted[:1]) == [(0, 0)]


def test_hand_checked_metrics():
    results = [
        evaluate.Result(
            phrase(1, [expected(["mleko"], 2), expected(["hleb"])]),
            items(("mleko", 1), ("hleb", 1), ("sir", 1)),
        ),
        evaluate.Result(phrase(2, [expected(["jaja"], 6)]), []),
        evaluate.Result(phrase(3, []), []),
        evaluate.Result(phrase(4, []), items(("kafa", 1))),
    ]
    results[0].top1 = 1
    results[0].top5 = 2
    assert evaluate.metrics(results, True) == {
        "Item recall": 2 / 3,
        "Item precision": 2 / 4,
        "Quantity accuracy (matched pairs)": 1 / 2,
        "Exact item count (sentences)": 1 / 4,
        "Top-1 hit rate (expected items)": 1 / 3,
        "Top-5 hit rate (expected items)": 2 / 3,
    }
    empty = evaluate.metrics(results[2:])
    assert empty["Item recall"] is None
    assert empty["Item precision"] == 0
    assert empty["Quantity accuracy (matched pairs)"] is None
    assert empty["Exact item count (sentences)"] == 1 / 2


def write_inputs(tmp_path):
    phrases = [phrase(1, [expected(["mleko"], 2)]), phrase(2, [expected(["hleb"])]), phrase(3, [])]
    labels = tmp_path / "phrases.jsonl"
    recorded = tmp_path / "recorded.jsonl"
    labels.write_text("\n".join(p.model_dump_json() for p in phrases), encoding="utf-8")
    texts = [
        json.dumps({"items": [i.model_dump() for i in items(("mleko", 2))]}),
        '{"items": []}',
        '{"items": []}',
    ]
    recorded.write_text(
        "\n".join(
            evaluate.Recording(id=i, text=t, model="test-model").model_dump_json()
            for i, t in enumerate(texts, 1)
        ),
        encoding="utf-8",
    )
    return labels, recorded


def test_recorded_end_to_end_three_lines(tmp_path, monkeypatch):
    labels, recorded = write_inputs(tmp_path)
    for name in ("LLM_API_KEY", "LLM_MODEL", "LLM_PROVIDER", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    report = tmp_path / "report.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "korpa_api.ai.evaluate",
            "--phrases",
            str(labels),
            "--recorded",
            str(recorded),
            "--out",
            str(report),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    text = report.read_text(encoding="utf-8")
    assert "Smoke test only" in text and "Model: test-model" in text
    assert "Mode: recorded" in text and "Sentences: 3" in text
    assert "| Item recall | 50.0% | N/A |" in text
    assert "| Item precision | 100.0% | N/A |" in text
    assert "| Exact item count (sentences) | 66.7% | 100.0% |" in text
    assert "| 2 |" in text


def test_live_requires_config_and_record_requires_live(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "configured_extractor", lambda: None)
    assert evaluate.main(["--live", "--out", str(tmp_path / "out.md")]) == 2
    assert "--live requires LLM_PROVIDER" in capsys.readouterr().err
    with pytest.raises(SystemExit) as error:
        evaluate.main(["--record", str(tmp_path / "record.jsonl")])
    assert error.value.code == 2


def test_live_records_raw_response_and_waits(tmp_path, monkeypatch):
    labels, _ = write_inputs(tmp_path)
    raw = ' {"items": [{"phrase": "bad", "query": "x", "qty": 0}]} '
    calls = []

    class FakeExtractor:
        model = "test-model"

        async def extract_raw(self, sentence):
            calls.append(sentence)
            return raw

    waits = []

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(evaluate, "configured_extractor", lambda: FakeExtractor())
    monkeypatch.setattr(evaluate.asyncio, "sleep", sleep)
    recorded = tmp_path / "raw.jsonl"
    report = tmp_path / "live.md"
    assert (
        evaluate.main(
            ["--live", "--phrases", str(labels), "--record", str(recorded), "--out", str(report)]
        )
        == 0
    )
    rows = evaluate.read_recordings(recorded, evaluate.read_phrases(labels))
    assert all(row.text == raw and row.model == "test-model" for row in rows.values())
    assert waits == [6, 6] and len(calls) == 3
    assert (
        evaluate.main(
            [
                "--phrases",
                str(labels),
                "--recorded",
                str(recorded),
                "--out",
                str(tmp_path / "replay.md"),
            ]
        )
        == 0
    )


def test_recording_coverage_and_invalid_output(tmp_path):
    labels, recorded = write_inputs(tmp_path)
    phrases = evaluate.read_phrases(labels)
    recorded.write_text('{"id":1,"text":"invalid"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="ids must match"):
        evaluate.read_recordings(recorded, phrases)
    recorded.write_text('{"id":1,"text":"invalid"}\n' * 2, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        evaluate.read_recordings(recorded, phrases)
    labels.write_text(phrases[0].model_dump_json(), encoding="utf-8")
    recorded.write_text('{"id":1,"text":"invalid"}', encoding="utf-8")
    report = tmp_path / "invalid.md"
    assert (
        evaluate.main(["--phrases", str(labels), "--recorded", str(recorded), "--out", str(report)])
        == 0
    )
    assert "invalid outputs: 1" in report.read_text(encoding="utf-8")


def test_report_omits_amounts():
    p = phrase(1, [expected(["mleko"])])
    p.sentence = "mleko košta 1 dinar"
    report = evaluate.render_report(
        [evaluate.Result(p, [])], "fixture", "recorded", date(2026, 11, 21), False
    )
    assert "1 dinar" not in report


def test_database_retrieval_searches_every_query(client, monkeypatch):
    import asyncio

    original = evaluate.repository.search
    searched = []

    async def search(session, params, as_of):
        searched.append(params.q)
        assert params.category is None
        return await original(session, params, as_of)

    monkeypatch.setattr(evaluate.repository, "search", search)
    results = [
        evaluate.Result(
            phrase(1, [expected(["mleko"]), expected(["hleb"])]), items(("mleko", 1), ("kafa", 1))
        ),
        evaluate.Result(phrase(2, [expected(["čokolada"], category=2)]), items(("čokolada", 1))),
    ]
    asyncio.run(evaluate.retrieve(results, date(2026, 11, 21)))
    assert searched == ["mleko", "kafa", "čokolada"]
    assert (results[0].top1, results[0].top5) == (1, 1)
    assert (results[1].top1, results[1].top5) == (0, 0)
    assert evaluate.metrics(results, True)["Top-5 hit rate (expected items)"] == 1 / 3
