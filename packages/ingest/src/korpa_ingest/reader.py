"""Strict CSV contract: no repaired headers, barcodes, prices, or list types."""

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

HEADERS = (
    "KATEGORIJA",
    "NAZIV KATEGORIJE",
    "Naziv proizvoda",
    "Robna marka",
    "Barkod proizvoda",
    "Jedinica mere",
    "Naziv trgovca - formata",
    "Datum cenovnika",
    "Redovna cena",
    "Cena po jedinici mere",
    "Snižena cena",
    "Datum početka sniženja",
    "Datum kraja sniženja",
    "Stopa PDV",
    "VRSTA_CENOVNIKA",
)


class PriceRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    category: int
    category_name: str
    name: str
    brand: str
    barcode: str
    unit: str
    format_name: str
    list_date: date
    regular: int
    unit_price: int
    discounted: int | None
    disc_from: date | None
    disc_to: date | None
    vat: int
    kind: Literal["MESEČNI_PRESEK", "VAŽEĆI_CENOVNIK"]


@dataclass
class Report:
    rows_total: int = 0
    rows_valid: int = 0
    errors: Counter[str] = field(default_factory=Counter)
    samples: dict[str, list[int]] = field(default_factory=dict)

    def error(self, code: str, line: int = 0, count: int = 1) -> None:
        self.errors[code] += count
        bucket = self.samples.setdefault(code, [])
        if len(bucket) < 5:
            bucket.append(line)

    def as_dict(self) -> dict[str, object]:
        return {
            "rows_total": self.rows_total,
            "rows_valid": self.rows_valid,
            "errors": dict(self.errors),
            "sample_lines": self.samples,
        }


@dataclass
class Parsed:
    rows: list[PriceRow]
    report: Report


class RowError(ValueError):
    pass


def money(value: str, *, optional: bool = False) -> int | None:
    if value == "" and optional:
        return None
    if not re.fullmatch(r"[0-9]+\.[0-9]{2}", value):
        raise RowError("price")
    result = int(Decimal(value) * 100)
    if result > 2_147_483_647:
        raise RowError("price")
    return result


def parse_date(value: str, *, optional: bool = False) -> date | None:
    if value == "" and optional:
        return None
    if not re.fullmatch(r"[0-9]{2}-[0-9]{2}-[0-9]{4}", value):
        raise RowError("date")
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except ValueError as exc:
        raise RowError("date") from exc


def parse_row(values: list[str]) -> PriceRow:
    if len(values) != len(HEADERS):
        raise RowError("column_count")
    (
        category,
        category_name,
        name,
        brand,
        barcode,
        unit,
        format_name,
        list_date,
        regular,
        unit_price,
        discounted,
        disc_from,
        disc_to,
        vat,
        kind,
    ) = values
    if not re.fullmatch(r"[0-9]{13}", barcode):
        raise RowError("barcode")
    if not category.isascii() or not category.isdigit() or not 1 <= int(category) <= 25:
        raise RowError("category")
    if not category_name or not name or not format_name:
        raise RowError("required_text")
    if any("\x00" in text for text in values):
        raise RowError("nul_character")
    if unit not in {"kg", "g", "l", "ml", "kom", "pak"}:
        raise RowError("unit")
    if kind not in {"MESEČNI_PRESEK", "VAŽEĆI_CENOVNIK"}:
        raise RowError("list_type")
    if not re.fullmatch(r"[0-9]{1,2}", vat):
        raise RowError("vat")
    day = parse_date(list_date)
    start, end = parse_date(disc_from, optional=True), parse_date(disc_to, optional=True)
    price, per_unit = money(regular), money(unit_price)
    discount = money(discounted, optional=True)
    assert day is not None and price is not None and per_unit is not None
    if (discount is None and (start is not None or end is not None)) or (
        discount is not None and (start is None or end is None or start > end or discount > price)
    ):
        raise RowError("discount")
    if kind == "MESEČNI_PRESEK" and day.day != 1:
        raise RowError("snapshot_date")
    return PriceRow(
        category=int(category),
        category_name=category_name,
        name=name,
        brand=brand,
        barcode=barcode,
        unit=unit,
        format_name=format_name,
        list_date=day,
        regular=price,
        unit_price=per_unit,
        discounted=discount,
        disc_from=start,
        disc_to=end,
        vat=int(vat),
        kind="MESEČNI_PRESEK" if kind == "MESEČNI_PRESEK" else "VAŽEĆI_CENOVNIK",
    )


def read_csv(content: bytes) -> Parsed:
    report = Report()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        report.error("encoding")
        return Parsed([], report)
    # Header has no embedded delimiters, unlike category/product names in data rows.
    first = text.splitlines()[0] if text.splitlines() else ""
    delimiter = next(
        (
            d
            for d in (",", ";", "\t")
            if tuple(next(csv.reader([first], delimiter=d), [])) == HEADERS
        ),
        None,
    )
    if delimiter is None:
        # Diagnose the whole file without pretending its header matches the contract.
        report.rows_total = max(0, len(text.splitlines()) - 1)
        report.error("header", count=max(1, report.rows_total))
        return Parsed([], report)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    next(reader)
    rows: list[PriceRow] = []
    try:
        for values in reader:
            report.rows_total += 1
            try:
                rows.append(parse_row(values))
                report.rows_valid += 1
            except RowError as exc:
                report.error(str(exc), reader.line_num)
    except csv.Error:
        report.rows_total += 1
        report.error("csv_syntax", reader.line_num, count=report.rows_valid + 1)
        report.rows_valid = 0
        rows.clear()
    return Parsed(rows, report)
