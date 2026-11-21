# AGENTS.md — Korpa

## What this is
Korpa is an independent public-interest web app that turns Serbia's mandatory open-data grocery price lists into a
usable comparison tool: product search, price comparison across retail formats, a basket total per chain, a monthly
category price index, a data-quality report, and (later) an AI basket assistant and an MCP server.
It is NOT an official government site: never use state symbols, coats of arms or government branding, and keep the
disclaimer in the footer: "Nezavisan projekat zasnovan na otvorenim podacima. Nije povezan sa Ministarstvom."

Architecture, data model and phases: see `docs/ARCHITECTURE.md`. Current task: see `docs/tasks/`.

## Repository layout
- `apps/api`        FastAPI service (Python 3.12): REST + read-only GraphQL (Strawberry)
- `apps/web`        React 19 + Vite + TypeScript SPA
- `packages/ingest` Python package + CLI `korpa ingest` (used by the API and by GitHub Actions)
- `infra/`          docker-compose.yml (Postgres 16 + pgvector + pg_trgm), render.yaml
- `docs/`           ARCHITECTURE.md, data-notes.md, ADRs, tasks

## Commands (keep these working)
- `make dev`    start Postgres + api + web locally
- `make test`   pytest + vitest
- `make e2e`    playwright
- `make lint`   ruff + mypy + eslint + tsc --noEmit
- `korpa ingest --retailer <slug> | --all [--dry-run]`

## Data contract (official technical standard for retail price lists, effective 2026-09-01)
One consolidated UTF-8 CSV per retailer, file name stable and without a date (e.g. `cene_proizvoda_nazivtrgovca.csv`).
The delimiter is NOT specified by the standard: detect it (comma, semicolon, tab). Strip a BOM if present.
Decimal point `.`, 2 decimals. Empty fields stay empty (no "N/A", no "NULL"). Dates are `DD-MM-YYYY`.
Columns, in this exact order and spelling:

| # | Column | Notes |
|---|---|---|
| 1 | `KATEGORIJA` | category code 1–25 |
| 2 | `NAZIV KATEGORIJE` | category name |
| 3 | `Naziv proizvoda` | product name |
| 4 | `Robna marka` | brand |
| 5 | `Barkod proizvoda` | exactly 13 digits, keep as text (leading zeros matter) |
| 6 | `Jedinica mere` | kg, g, l, ml, kom, pak |
| 7 | `Naziv trgovca - formata` | retailer + store format; the finest location unit (there is no store ID) |
| 8 | `Datum cenovnika` | price list date |
| 9 | `Redovna cena` | regular price |
| 10 | `Cena po jedinici mere` | unit price |
| 11 | `Snižena cena` | discounted price, empty if none |
| 12 | `Datum početka sniženja` | discount start |
| 13 | `Datum kraja sniženja` | discount end |
| 14 | `Stopa PDV` | VAT as an integer, e.g. 10 or 20 |
| 15 | `VRSTA_CENOVNIKA` | `MESEČNI_PRESEK` (monthly snapshot, permanent) or `VAŽEĆI_CENOVNIK` (current list) |

A new `VAŽEĆI_CENOVNIK` is published on every price change and replaces the previous one; on the first day of each
month the list valid that day is also published as `MESEČNI_PRESEK` and kept forever.
Invalid rows are counted and reported per retailer, never silently dropped and never "fixed" by guessing.
Do not invent the portal API shape: verify it and record findings in `docs/data-notes.md`.

### Source compatibility profile `compat-2026-11.2`
Observed publisher variants are accepted only through exact, documented mappings. Every applied mapping is counted per retailer as a deviation in the quality report; it is never silent and never turns an invalid value into a valid one by guessing.
- `VRSTA_CENOVNIKA`: `MESECNI_PRESEK` -> `MESEČNI_PRESEK`, `VAZECI_CENOVNIK` -> `VAŽEĆI_CENOVNIK`.
- `Jedinica mere`: case-insensitive match to the six allowed units (`KG` -> `kg`), plus exact case-insensitive aliases `kom.` -> `kom`, `gr` -> `g`, `lit` -> `l`, counted as `unit_alias`. `JED`, `KO`, `M` and all other aliases remain errors.
- Prices with zero or one decimal using `.` are padded to two decimals without rounding (`100` -> `100.00`, `1000.1` -> `1000.10`), counted as `price_decimals` per mapped field. More than two decimals, commas, spaces, signs, leading-dot fractions, and thousands separators remain errors.
- Headers: only the aliases listed in `docs/data-notes.md`, each of the 15 columns mapped exactly once.
Any other variant stays an error. A new mapping needs a maintainer decision and a new profile id.

## Conventions
- Python: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, httpx, typer; ruff + mypy --strict on new code; pytest.
- API: REST for search, basket, categories and data quality; a read-only GraphQL endpoint (`/graphql`, Strawberry)
  for nested product -> prices -> history reads, with DataLoaders (no N+1), depth/complexity limits, and the schema
  exported for GraphQL Code Generator on the web side.
- Money is stored as INTEGER para (price x 100). Dates as DATE. Europe/Belgrade only for display.
- TypeScript strict, no `any`. TanStack Router + TanStack Query, Tailwind, Radix UI primitives, small typed components.
- UI copy in Serbian Latin with a Latin/Cyrillic toggle via transliteration; no hard-coded copy inside components.
- Accessibility: semantic HTML first, keyboard operable, visible focus, color is never the only signal (WCAG 2.2 AA).
- Every number shown to users carries its source date ("Cenovnik od 19.11.2026.").

## Storage budget (Neon free plan = 1 GB hard cap)
- Keep daily `price_changes` for 120 days; older history lives in `monthly_snapshots` (per format, last 3 months)
  and `monthly_prices` (one row per product per month). `korpa ingest` compacts older months after each run.
- Never store raw CSVs in the database.
- Log `pg_database_size` after each ingest; warn at 70 %, stop writing at 90 %.

## Secrets
Never commit secrets. Use `.env` (git-ignored) and keep `.env.example` with names only:
`DATABASE_URL`, `PORTAL_BASE_URL`, `CORS_ORIGINS`, `LLM_PROVIDER`, `LLM_API_KEY` (M5 only).

## Quality gates (CI must enforce)
- lint, typecheck, unit tests and build pass.
- Ingest tests run against fixture CSVs in `packages/ingest/tests/fixtures`, including broken ones:
  wrong delimiter, BOM, 12-digit barcode, empty price, bad date, unknown `VRSTA_CENOVNIKA`, missing column.
- Playwright smoke + axe on every page: zero violations (from M3).

## Workflow
- Small PRs, one task each, conventional commits, PR description: what, why, how to test.
- If something here or in the task is unclear, stop and ask in the PR instead of guessing.
- No tool or AI attribution anywhere: no `Co-authored-by` trailers, no "Generated with ..." lines, no tool names or
  task links in commits, branch names, PR/issue text or files. The maintainer is the only author.

## Out of scope for v1
User accounts, emails/notifications, store maps, mobile apps, scraping retailer websites.
