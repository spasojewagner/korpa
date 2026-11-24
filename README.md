# Korpa

**Korpa poredi cene iz otvorenih cenovnika trgovaca u Srbiji.** Pretraga, korpa po trgovinskom formatu,
najjeftinije po artiklu, indeks cena i kvalitet podataka dostupni su na jednom mestu. Svaka cena nosi datum izvora;
predloge pomoćnika korisnik proverava i potvrđuje.

> Nezavisan projekat zasnovan na otvorenim podacima. Nije povezan sa Ministarstvom.

[Live site](https://ai-korpa.vercel.app) · [API reference](https://korpa-api.onrender.com/docs) ·
[Interview walkthrough](docs/WALKTHROUGH.md) · [Launch drafts](docs/launch/demo-script.md)

## The problem and the publication rules

Retailer CSVs are useful public infrastructure, but comparing files by hand is difficult: names differ,
some rows fail validation, and a cheap partial basket can look better than a complete one.
Korpa turns the published observations into product search, dated comparisons, complete/partial baskets,
a fixed-base price index and an inspectable quality report.

The legal basis is article 6 of Serbia's Consumer Protection Law and the price-list rulebook,
including its technical-standard annex. The [official consolidated rulebook](https://pravno-informacioni-sistem.rs/eli/rep/sgrs/ministarstva/pravilnik/2026/76/3/reg),
reviewed on 2026-11-24, includes Gazette amendments 76/2026 and 98/2026 and applies from 2026-09-01.
Article 2 defines covered goods and retailers, including its revenue condition; this is not a claim that every
shop must publish. Article 4 distinguishes consolidated portal lists from individual shop lists and allows
the highest current price when outlets in a consolidated list differ. A format-level comparison therefore
does not promise the checkout price or stock at a particular shop.
The [retained official text and source notes](docs/launch/evidence/README.md) make this review reproducible.

The annex specifies a consolidated UTF-8 CSV, stable filename, current lists replaced on price changes,
and permanent first-of-month snapshots. Its logical fields map to the following repository contract
([reader.py](packages/ingest/src/korpa_ingest/reader.py), reviewed at `6eb264c` on 2026-11-24):

| # | Contract field | Meaning |
|---|---|---|
| 1 | `KATEGORIJA` | Category code |
| 2 | `NAZIV KATEGORIJE` | Category name |
| 3 | `Naziv proizvoda` | Published product name |
| 4 | `Robna marka` | Brand |
| 5 | `Barkod proizvoda` | Barcode, kept as text |
| 6 | `Jedinica mere` | Unit |
| 7 | `Naziv trgovca - formata` | Retailer and format |
| 8 | `Datum cenovnika` | Source list date |
| 9 | `Redovna cena` | Regular price |
| 10 | `Cena po jedinici mere` | Unit price |
| 11 | `Snižena cena` | Optional discounted price |
| 12 | `Datum početka sniženja` | Discount start |
| 13 | `Datum kraja sniženja` | Discount end |
| 14 | `Stopa PDV` | Integer VAT rate |
| 15 | `VRSTA_CENOVNIKA` | Current list or monthly snapshot |

The standard requires 13-digit barcodes, dot-decimal prices with two decimals, `DD-MM-YYYY` dates and empty
absent fields (annex §§5, 7–8, reviewed 2026-11-24). Korpa detects comma, semicolon or tab delimiters;
the standard does not mandate a particular delimiter. `compat-2026-11.3` accepts only documented
publisher variants and counts each deviation. Rejected rows are reported, never repaired by guessing.
**Compatibility limit:** the official Cyrillic annex uses an en dash in the format header and Cyrillic
values; the current exact profile rejects some of these, including Statovac's file. A failed Korpa import
is not itself evidence of legal non-compliance. See [data notes](docs/data-notes.md) and
[current retailer findings](docs/launch/retailers.md).

## Architecture

```mermaid
flowchart LR
    Portal["data.gov.rs retailer CSVs"] --> Actions["GitHub Actions: ingest and validate"]
    Actions --> Neon["Neon PostgreSQL"]
    Neon --> API["FastAPI on Render"]
    Neon --> Export["GitHub Actions: export static JSON"]
    Export --> Web["Static JSON + React on Vercel"]
    API --> Web
    API --> Graph["Read-only GraphQL"]
    API --> MCP["Read-only MCP /mcp/"]
    API --> Model["Optional Gemini / Groq extraction"]
```

The nightly workflow discovers portal resources, downloads and validates CSVs, applies atomic writes and
history compaction, refreshes analytics, and exports dated JSON before deploying the SPA. A push to `main`
exports and deploys without ingesting. Home, quality and index read static data first; search, product
and basket use the API. The nightly schedule is 03:17 UTC in [deploy.yml](.github/workflows/deploy.yml)
(configuration reviewed 2026-11-24). See [deployment and rollback](docs/deploy.md).

Python/FastAPI, SQLAlchemy/Alembic and PostgreSQL provide the backend; React, TypeScript, Vite and
TanStack Router/Query provide the web app. The current warm market design uses Onest and Lora,
paper surfaces, dark green actions and text labels alongside status colors
([theme source](apps/web/src/styles/theme.css), reviewed 2026-11-24).

## Decisions and tradeoffs

| Decision | Reason and record |
|---|---|
| Integer para | Exact money arithmetic, formatting only at the edge; [ADR 0003](docs/adr/0003-storage-static-and-index.md#money-and-storage) |
| Bounded history under the 1 GB project budget | Keep recent format detail and compact older months, warn/stop before the cap; [ADR 0003](docs/adr/0003-storage-static-and-index.md#money-and-storage) |
| Static data before the API | The free API can sleep; dated overview pages must remain useful; [ADR 0003](docs/adr/0003-storage-static-and-index.md#static-overviews) |
| REST and read-only GraphQL | Flat operations versus nested product/history reads, with bounded query cost; [ADR 0001](docs/adr/0001-rest-and-graphql.md) |
| Jevons index | Geometric mean of matched regular-price relatives, without invented expenditure weights; [ADR 0003](docs/adr/0003-storage-static-and-index.md#jevons-index) |
| No embeddings or pgvector in v1 | Reuse full-text/trigram search within the storage and memory budget; [ADR 0002](docs/adr/0002-ai-without-embeddings.md) |
| Checked model output | Model suggests search intent, database supplies product facts; [ADR 0002](docs/adr/0002-ai-without-embeddings.md) and [ADR 0003](docs/adr/0003-storage-static-and-index.md#checked-index-text) |

## Where the model is allowed to help

The basket model extracts phrases, search queries and pack quantities. For a goal such as lunch within a budget,
it may suggest ingredients marked as proposals and parse the stated budget. It must not supply product prices,
barcodes, retailers or product facts. Pydantic checks the extraction shape and bounds; ordinary catalog search
provides candidates, and the shopper chooses and confirms additions. The budget is parsed intent, not a price
fact; the displayed comparison is recomputed from selected catalog prices. The lowest per-item estimate can
span formats and excludes travel, delivery and availability.

Index notes receive only formatted facts from the computed index. The checker keeps a sentence only if its
numbers occur in its declared category facts, direction words agree, and it contains no banned causal or
prediction wording. Invalid sentences are dropped. This is a constrained text filter, not a proof that arbitrary
language is safe. Notes may be absent when configuration, provider availability or checks fail.

`LLM_PROVIDER=gemini|groq|auto` selects the provider; `LLM_API_KEY` and `LLM_MODEL` configure the primary provider.
Automatic mode uses a separate `GROQ_API_KEY` and optional `GROQ_MODEL`, with independent cooldowns and bounded
failover. Extraction caching and limits are in memory and reset on restart. Without configured model access,
the assistant is hidden and manual comparison remains available. GitHub evaluation secrets do not configure
Render automatically. See [configuration and evaluation](docs/ai-eval/README.md).

## Measured results

These are dated observations, not a live counter. [Frozen source JSON and hashes](docs/launch/evidence/README.md)
were captured on 2026-11-24 from the deployed site; both quality and index carry `as_of: 2026-11-24`.

| Measure | Observed result | Source and date |
|---|---:|---|
| Discovered publisher entries | 40 | `quality.json`, 2026-11-24 |
| Latest-run statuses | 3 ok, 30 partial, 7 failed | `quality.json`, 2026-11-24 |
| Entries with valid rows in their latest report | 33 | `rows_valid > 0`, `quality.json`, 2026-11-24 |
| Source rows represented by latest reports | 1,352,936 | Sum of `rows_total`, `quality.json`, 2026-11-24 |
| Accepted source rows | 1,005,169 | Sum of `rows_valid`, `quality.json`, 2026-11-24 |
| Accepted share | 74.30% | 1,005,169 / 1,352,936 × 100, same snapshot |
| Overall index, final November snapshot | 100.6976 | Code 0, `month: 2026-11-01`, `index.json`, 2026-11-24 |
| Overall index, provisional current point | 100.8754 | Code 0, `month: 2026-11-24`, `index.json`, 2026-11-24 |
| Provisional matched / excluded products | 82,720 / 1,018 | Same code 0 point, `index.json`, 2026-11-24 |

The index base is September 2026 = 100 (`base_month: 2026-09-01`, same source).
Counts describe source records, including historical snapshots and duplicates; they are not distinct products,
stores or current listings. Download failures have zero inspected rows, so the accepted share is not coverage
of every published row. Prior prices can remain available after a failed ingest. Approved deviations count as
accepted data, not strict standard conformance.

The [original live evaluation report](docs/ai-eval/results-live.md), dated 2026-11-24, records:

| Metric | Result |
|---|---:|
| Item recall | 93.7% |
| Item precision | 94.9% |
| Matched quantity accuracy | 97.3% |
| Exact item count per sentence | 98.0% |
| Retrieval top-1 | 82.3% |
| Retrieval top-5 | 88.6% |

Source: [successful run](https://github.com/spasojewagner/korpa/actions/runs/45417014920),
[artifact](https://github.com/spasojewagner/korpa/actions/runs/45417014920/artifacts/14933583105),
commit `8863481928925b9959f9ae5a3ad85da52590ed44`, 2026-11-24. All 50 unique sentence IDs completed with
database retrieval enabled and zero final invalid outputs. These are **mixed-provider failover results**:
Gemini `gemini-3.5-flash-lite` supplied 29 responses and Groq `openai/gpt-oss-20b` supplied 21.
The [verification](docs/ai-eval/verification.json), [per-sentence recording](docs/ai-eval/live.jsonl) and
[failover log](docs/ai-eval/failover-log.txt) retain attribution. There were 23 recovered failures and zero HTTP
429 events in this run: observed failover covered 503s, timeouts and one rejected JSON generation.
Quota cases have deterministic tests; this run is neither a single-model benchmark nor an unlimited-availability
guarantee. Retrieval counts unmatched expected items as misses; quantity accuracy counts only matched pairs.
Goal proposals and budget suitability are not scored by the named-product evaluation.

### Lighthouse verification

Measured on 2026-11-24 by Lighthouse 13.6.0 in the completed
[CI run](https://github.com/spasojewagner/korpa/actions/runs/45411937189), at the same source commit,
using the [lighthouse-reports artifact](https://github.com/spasojewagner/korpa/actions/runs/45411937189/artifacts/14928091653).
These are mobile production-build measurements with **mocked API/static data** and a seeded basket;
they do not measure live Render cold starts or real-user field performance.

| Route | Performance | Accessibility | Best practices | SEO |
|---|---:|---:|---:|---:|
| `/` | 100 | 100 | 100 | 100 |
| `/pretraga?q=mleko` | 100 | 100 | 100 | 100 |
| `/korpa` | 99 | 100 | 100 | 100 |
| `/podaci` | 100 | 100 | 100 | 100 |
| `/podaci/indeks` | 100 | 100 | 100 | 100 |

[Retained scores, report timestamps and hashes](docs/launch/evidence/2026-11-24/lighthouse-summary.json).
Lighthouse accessibility scores do not establish complete WCAG conformance.

## Screenshots

Production captures from 2026-11-24, without intercepted data or new model calls.
[Exact URLs, timestamps and viewport](docs/images/v1/provenance.json) accompany the images.
Screenshots preserve the deployed design and observed data; prices are not current-price promises.

![Korpa home with search and the warm market design](docs/images/v1/home.png)
Home: product search is the entry point; the data area is separate from shopping.

![Milk search with dated retailer offers](docs/images/v1/search.png)
Search: published names, price ranges and source-list dates, captured from `/pretraga?q=mleko`.

![Basket input and dated complete format totals](docs/images/v1/basket.png)
Basket: products added through the live search controls, with complete format totals.

![Expanded cheapest-per-item section for the same live basket](docs/images/v1/basket-split.png)
Split comparison: the same basket's actual item choices and source dates; this selection has no saving
against the cheapest complete format. Partial baskets remain labeled separately farther down the basket page.
Zero-valued offers, if shown, are source observations accepted by the current code and need review; they are not
a claim of free goods.

![Price index with method and dated series](docs/images/v1/index.png)
Index: the current provisional point and category table; the final snapshot and provisional point describe
different observations in the source JSON.

## Limits and next steps

Discovery is heuristic, format-level data cannot establish shop-level stock, and publisher mistakes can survive
structural validation. Barcodes identify products; names and packaging can still be inconsistent. Partial baskets
must remain labeled, and the per-item split minimizes price rather than shops visited. The index uses regular
prices, unweighted matched products and a lower observed median across formats; it is not Serbia's CPI or a
household cost-of-living index. Sparse categories can have no published value.

Free-host cold starts, stale exports, in-memory quotas and provider outages remain operational limits.
The 1 GB storage cap is the project's configured budget, not a claim about future hosting-plan allowances.
Historical architecture/task files contain plans superseded by code, notably pgvector and the original design.

Next: review the Cyrillic/en-dash compatibility gap, investigate zero prices and inconsistent publisher fields,
recheck failed sources, and extend evaluation to goal proposals before making quality claims about them.
TODO: record a demo and review the launch drafts, dataset licenses and attribution wording before manual publication.
No portal submission or release is implied by these materials.

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
CI also runs dependency audits, the recorded extraction smoke test, the Home size budget, and mobile Lighthouse with typed fixtures.


## Ingest and data maintenance

```sh
uv run --extra dev korpa ingest --retailer beltorg-doo-1 --dry-run
uv run --extra dev korpa ingest --all
uv run --extra dev python -m korpa_api.export_static
```

Choose a discovered organization slug; dry-run validates without database writes. The active compatibility profile
is `compat-2026-11.3`. [Data notes](docs/data-notes.md) explain mappings, per-rule errors and conditional downloads.
Accepted complete files can withdraw absent current listings; suspicious shrinkage retains previous current prices.
Recent daily history is bounded and older monthly history is compacted. Raw CSVs never enter persistent database
tables. See [ADR 0003](docs/adr/0003-storage-static-and-index.md) for the retention and budget policy.

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


Launch materials: [recording script](docs/launch/demo-script.md), [portal reuse draft](docs/launch/data-gov-rs.md),
[retailer email drafts](docs/launch/retailers.md), [CV and LinkedIn copy](docs/launch/cv.md).
