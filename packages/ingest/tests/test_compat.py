import csv
import io
from pathlib import Path

import pytest
from korpa_ingest.compat import PROFILE
from korpa_ingest.reader import HEADERS, read_csv

FIXTURES = Path(__file__).parent / "fixtures"


def csv_bytes(header: list[str], rows: list[list[str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def values() -> list[str]:
    return next(
        iter(
            list(
                csv.reader(
                    (FIXTURES / "good.csv").read_text(encoding="utf-8").splitlines(),
                    delimiter=";",
                )
            )[1:]
        )
    )


def test_only_approved_value_variants_are_valid_and_counted() -> None:
    row = values()
    row[5], row[14] = "KG", "VAZECI_CENOVNIK"
    parsed = read_csv(csv_bytes(list(HEADERS), [row]), profile=PROFILE)
    assert parsed.header_accepted and parsed.fully_processed
    assert parsed.report.rows_valid == 1
    assert parsed.rows[0].unit == "kg"
    assert parsed.rows[0].kind == "VAŽEĆI_CENOVNIK"
    assert not parsed.report.errors
    assert parsed.report.deviations == {"unit_case": 1, "list_type_ascii": 1}
    assert parsed.report.as_dict()["profile"] == PROFILE


@pytest.mark.parametrize("source", ["KG", "G", "L", "ML", "KOM", "PaK"])
def test_all_six_units_support_exact_case_variants(source: str) -> None:
    row = values()
    row[5] = source
    parsed = read_csv(csv_bytes(list(HEADERS), [row]), profile=PROFILE)
    assert parsed.report.rows_valid == 1
    assert parsed.rows[0].unit == source.lower()
    assert parsed.report.deviations == {"unit_case": 1}


def test_monthly_ascii_mapping_keeps_monthly_semantics() -> None:
    row = values()
    row[7], row[14] = "01-11-2026", "MESECNI_PRESEK"
    parsed = read_csv(csv_bytes(list(HEADERS), [row]), profile=PROFILE)
    assert parsed.report.rows_valid == 1
    assert parsed.rows[0].kind == "MESEČNI_PRESEK"
    assert not parsed.has_current
    assert parsed.report.deviations == {"list_type_ascii": 1}


@pytest.mark.parametrize("unit", ["kom.", "lit", " KG", "kilogram", "KＧ", "KG"])
def test_unlisted_units_remain_errors(unit: str) -> None:
    row = values()
    row[5] = unit
    parsed = read_csv(csv_bytes(list(HEADERS), [row]), profile=PROFILE)
    assert parsed.report.rows_valid == 0
    assert parsed.report.errors == {"unit": 1}
    assert not parsed.report.deviations


@pytest.mark.parametrize("kind", ["VAZECI", "vazeci_cenovnik", "MESECNI_PRESEK ", "CURRENT"])
def test_unlisted_list_types_remain_errors(kind: str) -> None:
    row = values()
    row[14] = kind
    parsed = read_csv(csv_bytes(list(HEADERS), [row]), profile=PROFILE)
    assert parsed.report.errors == {"list_type": 1}


def test_exact_lidl_header_alias_and_reordering() -> None:
    header = list(HEADERS)
    header[6] = " Naziv trgovca – formata "
    row = values()
    parsed = read_csv(csv_bytes(header[::-1], [row[::-1]]), profile=PROFILE)
    assert parsed.report.rows_valid == 1
    assert parsed.rows[0].barcode == row[4]
    assert parsed.report.deviations == {"header_alias": 1}
    assert not read_csv(csv_bytes(header, [row])).header_accepted


@pytest.mark.parametrize("variant", ["duplicate", "unknown", "missing", "extra"])
def test_header_requires_a_bijection(variant: str) -> None:
    header = list(HEADERS)
    if variant == "duplicate":
        header[0] = header[1]
    elif variant == "unknown":
        header[6] = "Naziv trgovca - format"
    elif variant == "missing":
        header.pop()
    else:
        header.append("Naziv trgovca – formata")
    parsed = read_csv(csv_bytes(header, [values()]), profile=PROFILE)
    assert not parsed.header_accepted
    assert not parsed.fully_processed
    assert parsed.report.errors == {"header": 1}


def test_every_failing_rule_is_counted_once_per_row() -> None:
    row = values()
    row[4], row[5], row[8], row[9], row[14] = "short", "lit", "", "invalid", "UNKNOWN"
    parsed = read_csv(csv_bytes(list(HEADERS), [row]), profile=PROFILE)
    assert parsed.report.rows_total == 1 and parsed.report.rows_valid == 0
    assert parsed.report.errors == {"barcode": 1}
    assert parsed.report.errors_by_rule == {"barcode": 1, "unit": 1, "price": 1, "list_type": 1}


def test_deviations_on_an_invalid_row_are_still_visible() -> None:
    row = values()
    row[4], row[5], row[14] = "short", "KG", "VAZECI_CENOVNIK"
    parsed = read_csv(csv_bytes(list(HEADERS), [row]), profile=PROFILE)
    assert parsed.report.errors == {"barcode": 1}
    assert parsed.report.deviations == {"unit_case": 1, "list_type_ascii": 1}


def test_incomplete_csv_does_not_become_cacheable() -> None:
    content = csv_bytes(list(HEADERS), [values()]) + b'"unterminated\n'
    parsed = read_csv(content, profile=PROFILE)
    assert parsed.header_accepted and not parsed.fully_processed
    assert not parsed.rows
    assert "csv_syntax" in parsed.report.errors
