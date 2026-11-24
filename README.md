# Korpa

**Transparentnost cena namirnica u Srbiji, iz otvorenih podataka.**
Open-data price transparency for Serbian groceries.

**Uživo:** https://ai-korpa.vercel.app · API: https://korpa-api.onrender.com/docs

Since September 2026, Serbian retailers must publish their price lists as machine-readable CSV files on the national
open data portal. Korpa turns those files into a tool people can actually use:

- search any product and compare its price across retail chains and store formats,
- build a basket and see which chain is cheapest for it,
- follow a monthly price index per product category,
- see which retailers publish complete, on-time data (a data-quality report),
- use read-only MCP tools for product search, price comparison and basket totals, grounded in real prices.

> Nezavisan projekat zasnovan na otvorenim podacima. Nije povezan sa Ministarstvom.
> Independent project built on open data. Not affiliated with any government body.

## Status
Project foundation and ingestion are implemented. The active `compat-2026-11.2` profile
imported usable prices from five live publishers: 76,673 valid source records of 82,546 checked.
Every accepted publisher variant is counted in [data notes](docs/data-notes.md).
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
comma-separated `CORS_ORIGINS` for other environments. Load real price lists with
`uv run --extra dev korpa ingest --all` and refresh the index and static files with
`uv run --extra dev python -m korpa_api.export_static`, then open the site: search, product comparison, basket,
data quality and about pages, in Latin or Cyrillic. The web app calls the API at `VITE_API_URL`
(build-time variable, default `http://127.0.0.1:8000`). `npm --prefix apps/web run size` checks
the Home JavaScript budget after a build.

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

CI installs locked dependencies and enforces schema/client drift checks, Python lint/types/tests,
migrations, frontend lint/types/tests, production build, and the keyboard browser smoke test.
Comparison pages, analytics, and deployment are later phases.

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
uses the approved `compat-2026-11.2` profile: two ASCII list types, exact unit case
normalization, the aliases `kom.`/`gr`/`lit`, exact padding of zero/one-decimal prices,
and the documented Lidl header alias are mapped. Headers map by name, with
all 15 columns present exactly once; whitespace and ordering may differ. The Python reader
still supports strict mode by omitting its explicit profile argument.

Each command prints one JSON report per selected retailer: source URL, dataset ID, license,
HTTP status, total and valid rows, grouped errors, and up to five source line numbers per error.
`errors` counts the first failing rule per invalid row; `errors_by_rule` also reports every
independently failing rule once per row. `deviations` counts all approved mappings, including
those on otherwise invalid rows, and `profile` identifies the interpretation. Rows with only
deviations are valid. Invalid files/rows are reported even when
valid rows from the same source are written. Conflicting duplicate prices are rejected.
Dry-run never opens a database connection or persists HTTP validators. Exit status is 0 for
clean imports/304 reports, 1 for data/download/discovery errors, and 2 for CLI usage or storage-limit
errors. No network call is made by fixture tests.

Current prices, names and formats are upserted atomically per retailer. Price history changes
only when price values change; old daily history expires after 120 days. Monthly snapshots
are retained permanently. Raw CSV data is never stored in the database. Database size is logged
before/after each run, warned at 70% of 1 GB, and writes are rolled back at 90%.

Accepted, fully processed current files also withdraw absent current listings for that
retailer. If the valid count falls below half the previous accepted run, `suspicious_shrink`
keeps all previous current prices and disables withdrawal. Historical observations are never
removed by withdrawal. Validators are cached for fully processed accepted-header files even
with invalid rows; changing the profile or resource URL forces a full download. A 304 retains
the previous quality report without rewriting prices.

Exact mappings, live observations, and the before/after Metro benchmark are in
[data notes](docs/data-notes.md) and [the recorded report](docs/portal-observations.json).

## PostgreSQL integration tests

REST endpoints, search rules, curl examples, and the dedicated 720k-price performance run are
documented in [the REST API guide](docs/rest-api.md).

The query-only `/graphql` endpoint, nested product example, bounds and reproducible latency
measurements are in [the product graph guide](docs/graphql-api.md). Run `make schema` and
`npm run codegen` after API contract or GraphQL operation changes; commit both schemas and
the typed client artifacts. Use Node 22 to match CI. Set `ENV=dev` to enable the interactive
GraphQL editor; introspection remains enabled in every environment.

Tests write only to a dedicated database named `korpa_test`. They refuse other database names.
Without `TEST_DATABASE_URL`, database integration tests are skipped; CI always sets it.

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

## AI configuration

AI basket extraction and checked index notes support `LLM_PROVIDER=gemini` or `groq`,
using `LLM_API_KEY` and `LLM_MODEL`. The manual evaluation workflow also offers Groq's
free-plan setup with a separate `GROQ_API_KEY` secret, conservative pacing and rate-limit
backoff. See [evaluation configuration](docs/ai-eval/README.md).

## MCP

The read-only Streamable HTTP endpoint is `https://korpa-api.onrender.com/mcp/`
(`/mcp` redirects there). It exposes exactly three tools: `search_products`,
`compare_prices`, and `cheapest_basket`. No API key is needed. Example configuration
for a client that supports remote MCP servers over HTTP:

```json
{
  "mcpServers": {
    "korpa": {
      "type": "http",
      "url": "https://korpa-api.onrender.com/mcp/"
    }
  }
}
```

Results include `as_of` and source price-list dates; amounts are integer para
(1/100 RSD). Prices come from retailers' open-data price lists on data.gov.rs.
Korpa is an independent project, not a state service. The endpoint uses stateless
JSON responses and read-only database transactions. Host and Origin checks remain
enabled for the deployed API, Korpa's web origin, and loopback development.
