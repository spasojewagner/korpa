# Korpa

**Transparentnost cena namirnica u Srbiji, iz otvorenih podataka.**
Open-data price transparency for Serbian groceries.

Since September 2026, Serbian retailers must publish their price lists as machine-readable CSV files on the national
open data portal. Korpa turns those files into a tool people can actually use:

- search any product and compare its price across retail chains and store formats,
- build a basket and see which chain is cheapest for it,
- follow a monthly price index per product category,
- see which retailers publish complete, on-time data (a data-quality report),
- later: an AI basket assistant ("ručak za 4 osobe do 2.000 din") and an MCP server, always grounded in real prices.

> Nezavisan projekat zasnovan na otvorenim podacima. Nije povezan sa Ministarstvom.
> Independent project built on open data. Not affiliated with any government body.

## Status
Project foundation and strict ingestion pipeline are implemented. Live files from five publishers
were downloaded and audited, but none matched the supplied contract. Usable five-retailer data
remains blocked on the contract decision described in [data notes](docs/data-notes.md).
See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and roadmap.

## Stack
FastAPI · REST + GraphQL (Strawberry) · PostgreSQL (Neon) · SQLAlchemy + Alembic · React 19 · TypeScript · Vite ·
TanStack Router/Query · Tailwind · Radix UI · GitHub Actions (CI + nightly ingest) · Playwright · pytest · Vitest

## Local setup

Requirements: Python 3.12, uv, Node.js 22.12+ (or a compatible newer LTS), Docker Compose v2,
and GNU Make. Run commands from the repository root.

```sh
uv sync --extra dev --frozen
npm ci
npm ci --prefix apps/web
cp .env.example .env
make dev
```

The empty example variables use local development defaults: Postgres at
`postgresql+psycopg://korpa:korpa@localhost:5432/korpa`, API at
`http://127.0.0.1:8000/health`, and web at `http://127.0.0.1:5173`.
These database credentials are for the local Compose service only. Set `DATABASE_URL` and a
comma-separated `CORS_ORIGINS` for other environments. The development page shows an honest
empty state and the required independence disclaimer; it offers a Latin/Cyrillic UI toggle.

On Windows PowerShell without Make, use `Copy-Item .env.example .env`, then:

```powershell
docker compose -f infra/docker-compose.yml up -d --wait
uv run --extra dev alembic -c apps/api/alembic.ini upgrade head
npm run dev
```

`npm run dev` runs API and web together. Ctrl+C stops both processes. Postgres stays running;
stop it with `docker compose -f infra/docker-compose.yml stop`.

## Checks

```sh
make lint
make test
make build
npm --prefix apps/web exec -- playwright install chromium
make e2e
```

Equivalent commands without Make:

```sh
uv run --extra dev ruff check .
uv run --extra dev mypy
uv run --extra dev pytest
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web test
npm --prefix apps/web run build
npm --prefix apps/web run e2e
```

CI installs locked dependencies and enforces Python lint/types/tests, migrations, frontend
lint/types/tests, production build, and the keyboard browser smoke test. Product API, GraphQL,
comparison pages, analytics, and deployment are later phases.

## Ingest

```sh
uv run --extra dev korpa ingest --retailer beltorg-doo-1 --dry-run
uv run --extra dev korpa ingest --retailer beltorg-doo-1
uv run --extra dev korpa ingest --all --dry-run
uv run --extra dev korpa ingest --all
```

With the virtual environment activated, `korpa ingest ...` works directly. Choose exactly one
of `--retailer <publisher-slug>` and `--all`. Discovery uses the portal's organization slug,
not a guessed chain name. An unknown slug prints available options. The portal client discovers
unambiguous consolidated CSV resources, strips a UTF-8 BOM, detects comma/semicolon/tab, and
requires the exact header order and spellings in AGENTS.md.

Each command prints one JSON report per selected retailer: source URL, dataset ID, license,
HTTP status, total and valid rows, grouped errors, and up to five source line numbers per error.
The first failing rule is counted per invalid row. Invalid files/rows are reported even when
valid rows from the same source are written. Conflicting duplicate prices are rejected.
Dry-run never opens a database connection or persists HTTP validators. Exit status is 0 for
clean imports/304, 1 for data/download/discovery errors, and 2 for CLI usage or storage-limit
errors. No network call is made by fixture tests.

Current prices, names and formats are upserted atomically per retailer. Price history changes
only when price values change; old daily history expires after 120 days. Monthly snapshots
are retained permanently. Raw CSV data is never stored in the database. Database size is logged
before/after each run, warned at 70% of 1 GB, and writes are rolled back at 90%.

The current live-data mismatch is intentional validation output, not a successful import of
usable prices. Exact observations and unresolved compatibility questions are in
[data notes](docs/data-notes.md) and [the recorded report](docs/portal-observations.json).

## PostgreSQL integration tests

Tests write only to a dedicated database named `korpa_test`. They refuse other database names.
Without `TEST_DATABASE_URL`, seven database integration tests are skipped; CI always sets it.

```sh
docker compose -f infra/docker-compose.yml up -d --wait
docker compose -f infra/docker-compose.yml exec -T db createdb -U korpa korpa_test
export TEST_DATABASE_URL=postgresql+psycopg://korpa:korpa@localhost:5432/korpa_test
uv run --extra dev pytest
```

In PowerShell replace `export ...` with
`$env:TEST_DATABASE_URL='postgresql+psycopg://korpa:korpa@localhost:5432/korpa_test'` and use
`$env:PYTHONUTF8='1'` when the terminal's default encoding is not UTF-8. Create the test database
only once. Tests apply migrations and clear their own tables between cases; never point the
test URL at a shared database.
