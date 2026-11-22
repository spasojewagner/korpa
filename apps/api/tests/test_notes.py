import asyncio
import json
from datetime import date

import pytest
from korpa_api.ai.llm import ModelError
from korpa_api.ai.notes import MAX_NOTES, facts, index_notes, parse_notes
from korpa_api.schemas import IndexCategory, IndexPoint, IndexResponse


def series(code: int, name: str, *values: float | None) -> IndexCategory:
    months = [date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)]
    return IndexCategory(
        code=code,
        name=name,
        points=[
            IndexPoint(
                month=month, value=value, n_products=40, n_excluded=0, provisional=month.month == 11
            )
            for month, value in zip(months, values, strict=False)
        ],
    )


INDEX = IndexResponse(
    as_of=date(2026, 11, 21),
    base_month=date(2026, 9, 1),
    categories=[
        series(0, "Ukupno", 100, 100.5, 100.9),
        series(5, "Hleb i pekarski proizvodi", 100, 102.0, 103.1),
        series(8, "Meso", 100, 101.0, 101.25),
        series(15, "Ulja i masti", 100, 99.0, 98.5),
        series(3, "Voće i povrće", 100, 100.2, None),
        series(9, "Riba", 100, None, None),
    ],
)


def note(text: str, *codes: int) -> dict[str, object]:
    return {"text": text, "codes": list(codes)}


def parse(*notes: dict[str, object]) -> list[str]:
    general, by_code = facts(INDEX)
    kept, _ = parse_notes(json.dumps({"notes": list(notes)}), general, by_code)
    return kept


def test_facts_use_the_newest_value_and_rank_rises_and_falls() -> None:
    general, by_code = facts(INDEX)
    assert general == "Podaci do 21.11.2026. Bazni mesec je septembar 2026, kada je indeks 100."
    assert list(by_code) == [0, 5, 8, 3, 15]
    # Same rounding as the web: index 101,3 but change 1,2 % (formatChange rounds the ratio).
    assert by_code[8].line == "[8] Meso: indeks 101,3, rast 1,2 %"
    assert by_code[5].line == "[5] Hleb i pekarski proizvodi: indeks 103,1, rast 3,1 %"
    assert by_code[3].line == "[3] Voće i povrće: indeks 100,2, rast 0,2 %"
    assert by_code[15].line == "[15] Ulja i masti: indeks 98,5, pad 1,5 %"
    assert by_code[15].direction == -1
    assert 9 not in by_code  # no value since the base month


def test_grounded_notes_are_kept() -> None:
    kept = parse(
        note("Ukupni indeks je 100,9, što je rast od 0,9 % od septembra 2026.", 0),
        note("Najviše su poskupeli hleb i pekarski proizvodi, za 3,1 %.", 5),
        note("Ulja i masti beleže pad od 1,5 %, dok je meso skuplje za 1,2 %.", 15, 8),
    )
    assert len(kept) == MAX_NOTES


@pytest.mark.parametrize(
    "bad",
    [
        note("Hleb i pekarski proizvodi su poskupeli za 3,2 %.", 5),  # number not in facts
        note("Hleb i pekarski proizvodi su poskupeli za 3.1 %.", 5),  # wrong decimal mark
        note("Hleb je poskupeo za 1,5 % od septembra 2026.", 5),  # number of another category
        note("Ulja i masti su poskupela za 1,5 % od baznog meseca.", 15),  # wrong direction
        note("Hleb i pekarski proizvodi beleže pad od 3,1 %.", 5),  # wrong direction
        note("Hleb je poskupeo 3,1 % zbog cene brašna u regionu.", 5),  # a cause
        note("Цене хлеба су порасле за 3,1 % од септембра.", 5),  # Cyrillic
        note("Hleb i pekarski proizvodi su poskupeli za 3,1 %.", 42),  # unknown code
        note("Hleb i pekarski proizvodi su poskupeli za 3,1 %."),  # no code
        note("Kratko.", 0),  # too short
    ],
)
def test_ungrounded_notes_are_dropped(bad: dict[str, object]) -> None:
    assert parse(bad) == []


def test_at_most_three_notes_and_invalid_json_is_an_error() -> None:
    text = "Ukupni indeks je 100,9 od septembra 2026."
    assert len(parse(*[note(text, 0)] * 5)) == MAX_NOTES
    general, by_code = facts(INDEX)
    with pytest.raises(ModelError):
        parse_notes("not json", general, by_code)
    with pytest.raises(ModelError):
        parse_notes('{"items": []}', general, by_code)


class FakeModel:
    model = "fake-model"

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[str] = []

    async def generate_json(
        self, system: str, user: str, schema: dict[str, object], timeout: float = 10
    ) -> str:
        self.calls.append(user)
        return self.answer


def test_index_notes_sends_only_facts() -> None:
    answer = json.dumps({"notes": [note("Ukupni indeks je 100,9 od septembra 2026.", 0)]})
    model = FakeModel(answer)
    kept, proposed = asyncio.run(index_notes(model, INDEX))
    assert (kept, proposed) == (["Ukupni indeks je 100,9 od septembra 2026."], 1)
    assert "[5] Hleb i pekarski proizvodi: indeks 103,1, rast 3,1 %" in model.calls[0]
    assert "Riba" not in model.calls[0]


def test_no_facts_means_no_call() -> None:
    model = FakeModel("{}")
    empty = IndexResponse(as_of=date(2026, 11, 21), base_month=date(2026, 9, 1), categories=[])
    assert asyncio.run(index_notes(model, empty)) == ([], 0)
    assert model.calls == []


def test_export_adds_notes_only_when_some_survive(monkeypatch: pytest.MonkeyPatch) -> None:
    from korpa_api import export_static

    good = json.dumps({"notes": [note("Ukupni indeks je 100,9 od septembra 2026.", 0)]})
    monkeypatch.setattr(export_static, "configured_model", lambda: FakeModel(good))
    assert asyncio.run(export_static.notes(INDEX)) == {
        "notes": {"model": "fake-model", "items": ["Ukupni indeks je 100,9 od septembra 2026."]}
    }
    bad = json.dumps({"notes": [note("Ukupni indeks je 101,0 od septembra 2026.", 0)]})
    monkeypatch.setattr(export_static, "configured_model", lambda: FakeModel(bad))
    assert asyncio.run(export_static.notes(INDEX)) == {}
    monkeypatch.setattr(export_static, "configured_model", lambda: FakeModel("not json"))
    assert asyncio.run(export_static.notes(INDEX)) == {}
    monkeypatch.setattr(export_static, "configured_model", lambda: None)
    assert asyncio.run(export_static.notes(INDEX)) == {}
