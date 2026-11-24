"""Offline-first evaluation of sentence extraction, optionally including catalog retrieval."""

import argparse
import asyncio
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from korpa_api import repository
from korpa_api.ai.llm import (
    ExtractedItem,
    Extractor,
    GroqExtractor,
    ModelError,
    configured_extractor,
    parse_extraction,
)
from korpa_api.database import async_database_url
from korpa_api.schemas import SearchParams
from korpa_api.translit import normalize_query

DATA = Path("docs/ai-eval")
RETRY_DELAYS = (6, 12, 24)
MAX_RETRY_WAIT = 300


class EvaluationError(ValueError):
    """A safe configuration or input-coverage error for CLI display."""


class ExpectedItem(BaseModel):
    query_terms: list[str] = Field(min_length=1)
    qty: int = Field(ge=1, le=99)
    category: int = Field(ge=1, le=25)


class Phrase(BaseModel):
    id: int
    sentence: str
    expected: list[ExpectedItem]


class Recording(BaseModel):
    model_config = ConfigDict(strict=True)
    id: int
    text: str
    model: str = "unknown (recording has no model metadata)"
    provider: str | None = None


def contains_terms(terms: list[str], target: str) -> bool:
    """A normalized term or its prefix stem (at least four letters) occurs in target."""
    normalized = normalize_query(target)
    for term in terms:
        word = normalize_query(term)
        if word in normalized:
            continue
        if not any(word[:length] in normalized for length in range(len(word) - 1, 3, -1)):
            return False
    return True


def match_items(
    expected: list[ExpectedItem], extracted: list[ExtractedItem]
) -> list[tuple[int, int]]:
    """Walk labels in order and consume the first unused matching extraction."""
    used: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for i, item in enumerate(expected):
        for j, actual in enumerate(extracted):
            if j not in used and contains_terms(item.query_terms, actual.query):
                pairs.append((i, j))
                used.add(j)
                break
    return pairs


@dataclass
class Result:
    phrase: Phrase
    items: list[ExtractedItem]
    error: str | None = None
    top1: int = 0
    top5: int = 0

    @property
    def pairs(self) -> list[tuple[int, int]]:
        return match_items(self.phrase.expected, self.items)

    @property
    def qty_correct(self) -> int:
        return sum(self.phrase.expected[i].qty == self.items[j].qty for i, j in self.pairs)

    @property
    def errors(self) -> int:
        return (
            len(self.phrase.expected)
            + len(self.items)
            - 2 * len(self.pairs)
            + len(self.pairs)
            - self.qty_correct
            + int(self.error is not None)
        )


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def metrics(results: list[Result], database: bool = False) -> dict[str, float | None]:
    expected = sum(len(r.phrase.expected) for r in results)
    extracted = sum(len(r.items) for r in results)
    matched = sum(len(r.pairs) for r in results)
    values = {
        "Item recall": ratio(matched, expected),
        "Item precision": ratio(matched, extracted),
        "Quantity accuracy (matched pairs)": ratio(sum(r.qty_correct for r in results), matched),
        "Exact item count (sentences)": ratio(
            sum(len(r.phrase.expected) == len(r.items) for r in results), len(results)
        ),
    }
    if database:
        values["Top-1 hit rate (expected items)"] = ratio(sum(r.top1 for r in results), expected)
        values["Top-5 hit rate (expected items)"] = ratio(sum(r.top5 for r in results), expected)
    return values


def read_phrases(path: Path) -> list[Phrase]:
    phrases = [
        Phrase.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]
    if not phrases or len({p.id for p in phrases}) != len(phrases):
        raise EvaluationError("phrases must have unique ids and contain at least one sentence")
    return phrases


def read_recordings(path: Path, phrases: list[Phrase]) -> dict[int, Recording]:
    rows = [
        Recording.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    recordings = {row.id: row for row in rows}
    if len(rows) != len(recordings):
        raise EvaluationError("duplicate recorded ids")
    if set(recordings) != {p.id for p in phrases}:
        raise EvaluationError(
            "recorded ids must match phrase ids exactly (missing or unexpected ids)"
        )
    return recordings


async def retrieve(results: list[Result], as_of: date) -> None:
    engine = create_async_engine(async_database_url())
    try:
        async with async_sessionmaker(engine)() as session, session.begin():
            await session.execute(sa.text("SET TRANSACTION READ ONLY"))
            for result in results:
                # Search every extraction, even false positives; labels never filter the search.
                candidates = [
                    (
                        await repository.search(session, SearchParams(q=item.query, limit=5), as_of)
                    ).items
                    for item in result.items
                ]
                for i, j in result.pairs:
                    expected = result.phrase.expected[i]
                    hits = [
                        candidate.category_code == expected.category
                        and contains_terms(expected.query_terms, candidate.name)
                        for candidate in candidates[j]
                    ]
                    result.top1 += int(bool(hits and hits[0]))
                    result.top5 += int(any(hits))
    finally:
        await engine.dispose()


def cell(text: str) -> str:
    text = re.sub(r"(?i)\b\d+(?:[.,]\d+)?\s*(?:dinara?|rsd|eur|\u20ac)\b", "[amount omitted]", text)
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_report(
    results: list[Result],
    model: str,
    mode: str,
    as_of: date,
    database: bool,
    providers: set[str] | None = None,
) -> str:
    lines = ["# Basket extraction evaluation", ""]
    if mode == "recorded":
        lines += [
            "**Smoke test only:** recorded responses may be hand-written fixtures; this replay is "
            "not evidence of live model quality.",
            "",
        ]
    lines += [
        f"- Model: {cell(model)}",
        f"- Date: {as_of.isoformat()} (Europe/Belgrade)",
        f"- Mode: {mode}; retrieval: {'enabled' if database else 'disabled'}",
        f"- Sentences: {len(results)}; "
        f"invalid outputs: {sum(r.error is not None for r in results)}",
        "",
        "N/A means a zero denominator. Retrieval counts unmatched expected items as misses.",
        "",
        "| Metric | Overall | No items expected |",
        "|---|---:|---:|",
    ]
    if providers:
        lines.insert(2, "- Providers: " + ", ".join(sorted(providers)))
    if providers and len(providers) > 1:
        lines.insert(
            3, "- Mixed-provider failover run; these are not single-model benchmark scores."
        )
    overall = metrics(results, database)
    empty = metrics([r for r in results if not r.phrase.expected], database)

    def percent(value: float | None) -> str:
        return "N/A" if value is None else f"{value:.1%}"

    for name, value in overall.items():
        lines.append(f"| {name} | {percent(value)} | {percent(empty[name])} |")
    lines += [
        "",
        "## Ten worst sentences",
        "",
        "Ranked by missed + extra items + incorrect matched quantities + invalid output; "
        "then retrieval misses when enabled. Ties use id order.",
        "",
        "| Id | Sentence | Expected (query × qty; category) | Extracted (query × qty) | Errors |",
        "|---|---|---|---|---:|",
    ]
    worst = sorted(
        results,
        key=lambda r: (
            -r.errors,
            -(len(r.phrase.expected) - r.top5) if database else 0,
            r.phrase.id,
        ),
    )[:10]
    for r in worst:
        expected = (
            "; ".join(
                f"{' '.join(i.query_terms)} × {i.qty}; category {i.category}"
                for i in r.phrase.expected
            )
            or "∅"
        )
        actual = "; ".join(f"{i.query} × {i.qty}" for i in r.items) or "∅"
        if r.error:
            actual += " (invalid model output)"
        lines.append(
            f"| {r.phrase.id} | {cell(r.phrase.sentence)} | {cell(expected)} | "
            f"{cell(actual)} | {r.errors} |"
        )
    return "\n".join(lines) + "\n"


async def extract_with_retry(extractor: Extractor, phrase: Phrase) -> str:
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            return await extractor.extract_raw(phrase.sentence)
        except ModelError as exc:
            cause = exc.__cause__
            transient = isinstance(cause, (httpx.TimeoutException, httpx.NetworkError)) or (
                isinstance(cause, httpx.HTTPStatusError)
                and cause.response.status_code in {429, 500, 502, 503, 504}
            )
            if not transient or attempt == len(RETRY_DELAYS):
                raise
            delay = RETRY_DELAYS[attempt]
            if isinstance(cause, httpx.HTTPStatusError):
                value = cause.response.headers.get("retry-after", "")
                try:
                    requested = float(value)
                except ValueError:
                    requested = 0
                if math.isfinite(requested) and requested > MAX_RETRY_WAIT:
                    raise EvaluationError(
                        f"{exc}; Retry-After exceeds {MAX_RETRY_WAIT} seconds. "
                        "Retry after the provider quota resets; completed recordings are retained."
                    ) from exc
                if math.isfinite(requested) and requested > 0:
                    delay = max(delay, math.ceil(requested))
            print(
                f"Phrase {phrase.id}: {exc}; retry {attempt + 1}/{len(RETRY_DELAYS)} "
                f"in {delay} seconds",
                file=sys.stderr,
            )
            await asyncio.sleep(delay)
    raise AssertionError("unreachable")


async def run(args: argparse.Namespace) -> None:
    extractor = configured_extractor() if args.live else None
    if args.live and extractor is None:
        raise EvaluationError(
            "--live requires LLM_PROVIDER=gemini|groq|auto, LLM_API_KEY and "
            "LLM_MODEL; auto also requires GROQ_API_KEY"
        )
    if args.database and not os.environ.get("DATABASE_URL", "").strip():
        raise EvaluationError("--database requires DATABASE_URL")
    phrases = read_phrases(args.phrases)
    recordings = {} if args.live else read_recordings(args.recorded, phrases)
    results: list[Result] = []
    interval = args.interval_seconds or (30 if isinstance(extractor, GroqExtractor) else 6)
    as_of = datetime.now(ZoneInfo("Europe/Belgrade")).date()
    used_models = set() if extractor else {r.model for r in recordings.values()}
    providers = set() if extractor else {r.provider for r in recordings.values() if r.provider}
    # Flush each raw response so interrupted live runs retain completed calls.
    record_file = args.record.open("w", encoding="utf-8") if args.record else None
    try:
        for index, phrase in enumerate(phrases):
            if extractor:
                if index:
                    await asyncio.sleep(interval)
                text = await extract_with_retry(extractor, phrase)
                model = extractor.model
                provider = getattr(extractor, "provider", None)
                used_models.add(model)
                if provider:
                    providers.add(provider)
                if record_file:
                    record_file.write(
                        Recording(
                            id=phrase.id, text=text, model=model, provider=provider
                        ).model_dump_json(exclude_none=True)
                        + "\n"
                    )
                    record_file.flush()
            else:
                text = recordings[phrase.id].text
            try:
                # Goal proposals are suggestions the shopper confirms; only named products count.
                results.append(
                    Result(phrase, [i for i in parse_extraction(text).items if not i.proposed])
                )
            except ModelError:
                results.append(Result(phrase, [], error="invalid model output"))
    finally:
        if record_file:
            record_file.close()
    if args.database:
        await retrieve(results, as_of)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        render_report(
            results,
            ", ".join(sorted(used_models)),
            "live" if args.live else "recorded",
            as_of,
            args.database,
            providers,
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--recorded", type=Path, default=DATA / "recorded.jsonl")
    modes.add_argument("--live", action="store_true")
    parser.add_argument("--record", type=Path, help="save raw responses (requires --live)")
    parser.add_argument("--database", action="store_true", help="also evaluate catalog retrieval")
    parser.add_argument("--out", type=Path, default=DATA / "results.md")
    parser.add_argument("--phrases", type=Path, default=DATA / "phrases.jsonl")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        choices=range(6, 61),
        metavar="6..60",
        help="pause between live sentences (default: groq 30, gemini 6)",
    )
    args = parser.parse_args(argv)
    if args.record and not args.live:
        parser.error("--record requires --live")
    if args.record and args.record.resolve() in {args.phrases.resolve(), args.out.resolve()}:
        parser.error("--record must not overwrite phrases or the report")
    if args.out.resolve() in {args.phrases.resolve(), args.recorded.resolve()}:
        parser.error("--out must not overwrite phrases or recordings")
    try:
        asyncio.run(run(args))
    except (OSError, ValueError, ModelError, sa.exc.SQLAlchemyError) as exc:
        # ModelError already carries a sanitized provider status/message. Keep database
        # and other exception details private (URLs and SQL parameters may contain secrets).
        detail = str(exc) if isinstance(exc, (EvaluationError, ModelError)) else type(exc).__name__
        print(f"Evaluation failed: {detail}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
