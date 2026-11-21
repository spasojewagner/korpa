from pathlib import Path

import pytest
from korpa_ingest.normalize import normalize
from korpa_ingest.reader import money, read_csv

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("filename", ["good.csv", "comma.csv", "tab.csv", "bom.csv"])
def test_delimiters_and_exact_values(filename: str) -> None:
    parsed = read_csv((FIXTURES / filename).read_bytes())
    assert parsed.report.rows_total == parsed.report.rows_valid == 2
    assert not parsed.report.errors
    assert parsed.rows[0].barcode == "0001234567890"
    assert parsed.rows[0].regular == 12999
    assert parsed.rows[0].discounted is None
    assert parsed.rows[0].brand == ""
    assert parsed.rows[1].discounted == 9999
    assert parsed.rows[1].list_date.isoformat() == "2026-11-01"


@pytest.mark.parametrize(
    ("filename", "code"),
    [
        ("barcode.csv", "barcode"),
        ("empty-price.csv", "price"),
        ("bad-date.csv", "date"),
        ("unknown-type.csv", "list_type"),
        ("missing-column.csv", "header"),
        ("wrong-delimiter.csv", "header"),
        ("uppercase-unit.csv", "unit"),
        ("bad-discount.csv", "discount"),
        ("snapshot-date.csv", "snapshot_date"),
        ("decimal-comma.csv", "price"),
        ("extra-field.csv", "column_count"),
        ("category.csv", "category"),
        ("bad-utf8.csv", "encoding"),
    ],
)
def test_invalid_rows_are_reported(filename: str, code: str) -> None:
    parsed = read_csv((FIXTURES / filename).read_bytes())
    assert not parsed.rows
    assert parsed.report.rows_valid == 0
    assert parsed.report.errors == {code: 1}


def test_mixed_file_preserves_valid_rows_and_reports_invalid() -> None:
    parsed = read_csv((FIXTURES / "mixed.csv").read_bytes())
    assert parsed.report.rows_total == 3
    assert parsed.report.rows_valid == 2
    assert parsed.report.errors == {"barcode": 1}
    assert parsed.report.samples == {"barcode": [4]}


def test_conflicting_duplicates_are_all_rejected() -> None:
    parsed = read_csv((FIXTURES / "good.csv").read_bytes())
    original = parsed.rows[0]
    parsed.rows = [original, original.model_copy(update={"regular": 13000})]
    parsed.report.rows_total = parsed.report.rows_valid = 2
    normalized = normalize(parsed)
    assert normalized.rows == []
    assert normalized.report.rows_valid == 0
    assert normalized.report.errors == {"conflicting_duplicate": 2}


def test_identical_duplicates_collapse_without_inventing_errors() -> None:
    parsed = read_csv((FIXTURES / "good.csv").read_bytes())
    parsed.rows = [parsed.rows[0], parsed.rows[0]]
    assert len(normalize(parsed).rows) == 1


def test_money_never_uses_binary_float_rounding() -> None:
    assert money("0.29") == 29
    assert money("21474836.47") == 2147483647
    with pytest.raises(ValueError):
        money("21474836.48")
