"""Strict values with an optional, explicit source compatibility profile."""

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from korpa_ingest.compat import (
    EXTENDED_VALUE_PROFILES,
    HEADER_ALIASES,
    LIST_TYPES,
    NEW_HEADER_ALIASES,
    PROFILE,
    PROFILES,
    UNIT_ALIASES,
    UNITS,
    cyrillic_header,
)

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
    deviations: Counter[str] = field(default_factory=Counter)
    errors_by_rule: Counter[str] = field(default_factory=Counter)
    profile: str | None = None
    retries: int = 0

    def error(self, code: str, line: int = 0, count: int = 1) -> None:
        self.errors[code] += count
        self.errors_by_rule[code] += count
        bucket = self.samples.setdefault(code, [])
        if len(bucket) < 5:
            bucket.append(line)

    def as_dict(self) -> dict[str, object]:
        return {
            "rows_total": self.rows_total,
            "rows_valid": self.rows_valid,
            "errors": dict(self.errors),
            "sample_lines": self.samples,
            "errors_by_rule": dict(self.errors_by_rule),
            "deviations": dict(self.deviations),
            "profile": self.profile,
            "retries": self.retries,
        }


@dataclass
class Parsed:
    rows: list[PriceRow]
    report: Report
    header_accepted: bool = False
    fully_processed: bool = False
    has_current: bool = False


class RowError(ValueError):
    def __init__(self, *codes: str) -> None:
        self.codes = tuple(dict.fromkeys(codes))
        super().__init__(self.codes[0])


def money(value: str, *, optional: bool = False, report: Report | None = None) -> int | None:
    if value == "" and optional:
        return None
    if (
        report is not None
        and report.profile in EXTENDED_VALUE_PROFILES
        and re.fullmatch(r"[0-9]+(?:\.[0-9])?", value)
    ):
        whole, _, fractional = value.partition(".")
        value = whole + "." + fractional.ljust(2, "0")
        report.deviations["price_decimals"] += 1
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
        return date(int(value[6:]), int(value[3:5]), int(value[:2]))
    except ValueError as exc:
        raise RowError("date") from exc


def parse_row(values: list[str], report: Report | None = None) -> PriceRow:
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
    if report is not None and report.profile in PROFILES:
        if kind in LIST_TYPES:
            kind = LIST_TYPES[kind]
            report.deviations["list_type_ascii"] += 1
        if (
            report.profile in EXTENDED_VALUE_PROFILES
            and unit.isascii()
            and unit.lower() in UNIT_ALIASES
        ):
            unit = UNIT_ALIASES[unit.lower()]
            report.deviations["unit_alias"] += 1
        elif unit.isascii() and unit.lower() in UNITS and unit != unit.lower():
            unit = unit.lower()
            report.deviations["unit_case"] += 1
    errors: list[str] = []
    if not re.fullmatch(r"[0-9]{13}", barcode):
        errors.append("barcode")
    if not category.isascii() or not category.isdigit() or not 1 <= int(category) <= 25:
        errors.append("category")
    if not category_name or not name or not format_name:
        errors.append("required_text")
    if any("\x00" in text for text in values):
        errors.append("nul_character")
    if unit not in UNITS:
        errors.append("unit")
    if kind not in {"MESEČNI_PRESEK", "VAŽEĆI_CENOVNIK"}:
        errors.append("list_type")
    if not re.fullmatch(r"[0-9]{1,2}", vat):
        errors.append("vat")
    dates: list[date | None] = []
    for value, optional in ((list_date, False), (disc_from, True), (disc_to, True)):
        try:
            dates.append(parse_date(value, optional=optional))
        except RowError:
            dates.append(None)
            errors.append("date")
    prices: list[int | None] = []
    for value, optional in ((regular, False), (unit_price, False), (discounted, True)):
        try:
            prices.append(money(value, optional=optional, report=report))
        except RowError:
            prices.append(None)
            errors.append("price")
    day, start, end = dates
    price, per_unit, discount = prices
    # Presence rules are independent of parsing errors in other price/date fields.
    # Numeric and chronological comparisons require only their own parsed operands.
    if (
        (discounted == "" and (disc_from != "" or disc_to != ""))
        or (discounted != "" and (disc_from == "" or disc_to == ""))
        or (start is not None and end is not None and start > end)
        or (discount is not None and price is not None and discount > price)
    ):
        errors.append("discount")
    if kind == "MESEČNI_PRESEK" and day is not None and day.day != 1:
        errors.append("snapshot_date")
    if errors:
        raise RowError(*errors)
    assert day is not None and price is not None and per_unit is not None
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


def header_order(header: list[str], profile: str | None) -> list[int] | None:
    if profile is None:
        return list(range(15)) if tuple(header) == HEADERS else None
    if profile == PROFILE and (translated := cyrillic_header(header)) is not None:
        # Cyrillic names must equal canonical names, without applying Latin aliases.
        mapped = [value if value in HEADERS else None for value in translated]
    else:
        aliases = HEADER_ALIASES | NEW_HEADER_ALIASES if profile == PROFILE else HEADER_ALIASES
        mapped = [aliases.get(value.strip()) for value in header]
    if len(mapped) != 15 or set(mapped) != set(HEADERS):
        return None
    return [mapped.index(name) for name in HEADERS]


def read_csv(content: bytes, *, profile: str | None = None) -> Parsed:
    if profile is not None and profile not in PROFILES:
        raise ValueError("Unknown compatibility profile")
    report = Report(profile=profile)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        report.error("encoding")
        return Parsed([], report)
    first = text.partition("\n")[0].rstrip("\r")
    delimiter: str | None = None
    order: list[int] | None = None
    for candidate in (",", ";", "\t"):
        try:
            header = next(csv.reader([first], delimiter=candidate, strict=True), [])
        except csv.Error:
            continue
        order = header_order(header, profile)
        if order is not None:
            delimiter = candidate
            if tuple(header) != HEADERS:
                report.deviations["header_alias"] += 1
            break
    if delimiter is None or order is None:
        report.rows_total = max(0, len(text.splitlines()) - 1)
        report.error("header", count=max(1, report.rows_total))
        return Parsed([], report)
    parsed = Parsed([], report, header_accepted=True)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    next(reader)
    try:
        for raw_values in reader:
            report.rows_total += 1
            values = [raw_values[i] for i in order] if len(raw_values) == 15 else raw_values
            if len(values) == 15 and values[14] in {"VAŽEĆI_CENOVNIK", "VAZECI_CENOVNIK"}:
                parsed.has_current = True
            try:
                parsed.rows.append(parse_row(values, report))
                report.rows_valid += 1
            except RowError as exc:
                report.error(str(exc), reader.line_num)
                for code in exc.codes[1:]:
                    report.errors_by_rule[code] += 1
    except csv.Error:
        report.rows_total += 1
        report.error("csv_syntax", reader.line_num, count=report.rows_valid + 1)
        report.rows_valid = 0
        parsed.rows.clear()
        return parsed
    parsed.fully_processed = True
    return parsed
