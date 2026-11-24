# Interview walkthrough

Code review baseline: `6eb264c3a2877ff23530dde057294df474903878`, 2026-11-24.
Each section covers a functional module and names its implementation files; small helpers and generated
contracts are included with their owner. Historical tasks describe intent, while this guide describes the
implemented system. Measurements belong to the dated [case study](../README.md#measured-results).

## Portal discovery and downloading

[`portal.py`](../packages/ingest/src/korpa_ingest/portal.py) discovers datasets through the portal's udata API.
It searches several Serbian spellings, follows same-origin pagination and deduplicates dataset identities.
It accepts unambiguous CSV resources with recognized consolidated-list filenames rather than scraping shops.
Conditional requests reuse ETag or Last-Modified, while bounded retries handle timeouts and server errors.
This keeps discovery explicit and avoids downloading unchanged bodies unnecessarily.
Unrecognized filenames, ambiguous resources, changed metadata or unavailable servers can leave a publisher out.

## CSV validation and compatibility

[`reader.py`](../packages/ingest/src/korpa_ingest/reader.py) decodes UTF-8, removes a BOM and detects the delimiter.
It validates headers and typed fields before producing immutable price rows.
[`compat.py`](../packages/ingest/src/korpa_ingest/compat.py) contains versioned exact mappings, with every applied deviation counted.
The profile pads approved decimal representations without rounding and never invents a barcode or missing price.
Error samples retain source lines, first-error counts and independent per-rule counts for diagnosis.
Structural validation is deliberately bounded: accepted zero prices and exact-header gaps can still make the resulting comparison misleading or incomplete.
The official Cyrillic/en-dash form can fail this profile, so parser failure is not a legal conclusion.

## Normalization and relational model

[`normalize.py`](../packages/ingest/src/korpa_ingest/normalize.py) groups validated rows and handles repeated identities.
Identical source records can collapse into one write, while conflicting duplicate prices are rejected and reported.
[`db.py`](../packages/ingest/src/korpa_ingest/db.py) defines products, retailers, formats, current prices, history and ingest audits.
Products join by textual barcode, preserving leading zeros, while each retailer's published names remain separately available.
Integer para makes sums exact and source dates stay separate from processing timestamps.
Shared barcodes with inconsistent names or units can still need human review; matching identity does not establish equivalent packaging semantics.

## Bulk writes, withdrawal and storage

[`store.py`](../packages/ingest/src/korpa_ingest/store.py) uses transaction-local staging, COPY and set-based upserts.
Retailer advisory locks serialize competing imports and publisher writes are atomic.
Accepted complete current files can withdraw missing listings, but rejected, stale or suspiciously shrunken files cannot erase newer current data.
Daily history is retained for 120 days and monthly format detail for three months, with older months compacted to product summaries.
The storage guard warns at 70% and stops writes at 90% of the configured 1 GB budget.
Compaction loses old format detail, and a first-computed compacted median is retained even when late observations widen other aggregates.
These are code policies reviewed on 2026-11-24, not current provider-plan promises.

## CLI orchestration and migrations

[`cli.py`](../packages/ingest/src/korpa_ingest/cli.py) selects all sources or a discovered retailer slug and prints structured reports.
Dry-run performs discovery and validation without opening a database connection.
The CLI imports the ingest package rather than depending on the API package, keeping that layer usable independently.
[`apps/api/alembic`](../apps/api/alembic) evolves tables, extensions, search normalization and history views in versioned migrations.
The deployment performs migration before ingestion and export, so schema errors stop later steps.
An interrupted job, failed migration or storage stop needs operational attention; reporting bad rows is intentionally different from a process crash.

## API application, sessions and errors

[`main.py`](../apps/api/src/korpa_api/main.py) creates FastAPI, middleware, lifecycle-managed database sessions and the MCP transport.
[`database.py`](../apps/api/src/korpa_api/database.py) translates connection URLs for the async driver.
[`routes.py`](../apps/api/src/korpa_api/routes.py) and [`schemas.py`](../apps/api/src/korpa_api/schemas.py) enforce request bounds and return typed responses.
[`problems.py`](../apps/api/src/korpa_api/problems.py) makes failures explicit through RFC 9457 problem responses.
Successful GET responses receive a short public cache lifetime, while prices retain their source-list dates and comparison date.
Bad environment configuration, a sleeping service or an unavailable database can still prevent dynamic pages from loading.

## Search and text normalization

[`repository.py`](../apps/api/src/korpa_api/repository.py) builds bounded product search using full-text and trigram indexes.
[`translit.py`](../apps/api/src/korpa_api/translit.py) transliterates Serbian queries and mirrors the database normalization, including diacritics and the special handling of đ.
An exact barcode query has a separate identity match; text ranking combines rank, similarity, prefix preference and format coverage.
Without text, a category request ranks products by format coverage and stable name/barcode ordering.
The PostgreSQL simple configuration avoids pretending that a Serbian stemmer is available.
Synonyms, uncommon names and broad ingredient phrases can still retrieve poor candidates, which is why the shopper confirms the selection.

## Pricing, baskets and split shopping

[`pricing.py`](../apps/api/src/korpa_api/pricing.py) defines one effective-price expression shared by the interfaces.
A discount applies only within its inclusive date bounds, with absent bounds treated as open.
The basket repository multiplies integer amounts by quantities and ranks complete format totals before partial results.
The split calculation takes each item's cheapest offer and uses stable format-name/id tie breaks.
It returns the number of selected formats and a saving against the best complete format only when that baseline exists.
It does not optimize journeys or the minimum number of shops, and it cannot prove availability at a particular outlet.

## Read-only GraphQL and generated contracts

[`gql/schema.py`](../apps/api/src/korpa_api/gql/schema.py) and [`types.py`](../apps/api/src/korpa_api/gql/types.py) expose nested product, price and history reads without mutations.
[`context.py`](../apps/api/src/korpa_api/gql/context.py) creates request-scoped DataLoaders and serializes their shared async session access.
This batches relationships without sharing cached responses between users or issuing one query per product.
[`limits.py`](../apps/api/src/korpa_api/gql/limits.py) and [`router.py`](../apps/api/src/korpa_api/gql/router.py) bound graph expansion and reject invalid operations before resolution.
[`export_openapi.py`](../apps/api/src/korpa_api/export_openapi.py), the exported SDL, and [`codegen.yml`](../apps/web/codegen.yml) feed generated TypeScript contracts, with CI rejecting drift.
Expensive nesting and oversized results fail explicitly; historical prices cannot reconstruct discount windows that were never retained.

## Index and review signals

[`analytics.py`](../apps/api/src/korpa_api/analytics.py) computes a fixed-base Jevons index over matched regular-price medians.
It excludes undefined or extreme relatives and suppresses the value when too few usable products remain.
First-of-month snapshots are final, while current-price points are calculated on read and clearly marked provisional.
The same module detects price jumps, cross-format outliers and discounts following a jump using explicit rules.
Ratios above the configured sanity bound are reported as suspected data errors instead of ordinary signals.
Neither signals nor the index establish legal violations, causes of price changes or official inflation; missing products and source errors constrain interpretation.
See [signals.md](signals.md) for the rule boundaries and [ADR 0003](adr/0003-storage-static-and-index.md) for the index tradeoff.

## Static export and deployment

[`export_static.py`](../apps/api/src/korpa_api/export_static.py) refreshes analytics and writes categories, quality, index and signals JSON.
It can also attach optional checked notes, but data export remains useful when model configuration or generation fails.
The [deploy workflow](../.github/workflows/deploy.yml) migrates, optionally ingests, exports and deploys the static site.
Scheduled/manual runs ingest; pushes to main export without re-downloading retailer lists.
[`infra/render.yaml`](../infra/render.yaml), local Compose and the [deployment guide](deploy.md) describe the API and database connections.
A stale successful export can remain visible after a failed refresh, so static availability must not be confused with fresh source data.

## Model extraction and catalog candidates

[`ai/llm.py`](../apps/api/src/korpa_api/ai/llm.py) defines provider adapters, prompts and the extraction parser.
The model turns grocery intent into queries and quantities, with bounded ingredient proposals and a parsed optional budget.
It is not authorized to supply prices, barcodes or retailer facts.
[`ai/basket.py`](../apps/api/src/korpa_api/ai/basket.py) caches validated extraction and retrieves real catalog candidates through ordinary search.
The cache avoids repeat model work but candidates are still fetched from the database for each response.
Valid JSON can still express a wrong quantity or poor ingredient choice, so validation and user confirmation solve different problems.

## Provider failover and limits

[`ai/failover.py`](../apps/api/src/korpa_api/ai/failover.py) coordinates providers sequentially with independent cooldowns and bounded retry behavior.
It distinguishes recoverable quota/transient failures from errors that should not silently switch providers.
Provider/model provenance is attached to evaluation recordings rather than inferred from requested configuration.
[`ai/limits.py`](../apps/api/src/korpa_api/ai/limits.py) adds in-memory client and daily request accounting to protect the configured quota.
State resets on restart and is not a distributed limiter across multiple processes.
If both providers are unavailable the request can still fail; the successful mixed-provider run does not guarantee future quota or uptime.

## Checked index notes

[`ai/notes.py`](../apps/api/src/korpa_api/ai/notes.py) builds a small set of formatted index facts and requests short Serbian notes.
Each candidate sentence declares the categories it discusses.
The checker compares numeric tokens with those facts, checks rise/fall wording and blocks listed causal or prediction words.
Invalid sentences are dropped without trying to repair their meaning.
The export omits notes when no checked text remains, and the interface treats the section as optional.
The word filters are deliberately limited and cannot prove every possible sentence's semantics or explain real economic causes.

## Read-only MCP

[`mcp_server.py`](../apps/api/src/korpa_api/mcp_server.py) exposes product search, price comparison and cheapest-basket tools using Streamable HTTP.
The tools reuse the repository and pricing functions instead of calculating alternative prices for model clients.
Responses retain integer para, comparison dates and source-list dates.
Read-only database transactions, bounded inputs, Host/Origin checks and middleware rate limits constrain access.
The remote endpoint is `/mcp/`, with the mount redirect documented in the README client example.
Clients still need to support this transport and can encounter cold starts or rate limits; the server does not provide purchasing or write operations.

## Web shell, design and language

[`router.tsx`](../apps/web/src/router.tsx) and the layout split shopping routes from the Podaci area with lazy page modules.
[`styles/theme.css`](../apps/web/src/styles/theme.css) defines the current warm palette, Onest/Lora fonts, focus behavior and semantic tokens.
[`i18n`](../apps/web/src/i18n) owns Serbian copy, script state and transliteration, while published product names stay as source data.
[`components`](../apps/web/src/components) supplies reusable prices, dates, badges, product cards, comparisons and state views.
[`lib/format.ts`](../apps/web/src/lib/format.ts) centralizes currency/date formatting and [`lib/meta.ts`](../apps/web/src/lib/meta.ts) updates page metadata.
Keyboard focus, long names, reduced motion, text contrast and small screens need browser checks even when the types compile.

## Web data access and pages

[`lib/api.ts`](../apps/web/src/lib/api.ts) uses generated response types and static-first overview requests, with explicit network failures.
[`lib/query.tsx`](../apps/web/src/lib/query.tsx) and page queries handle asynchronous state without loading every data dependency on Home.
[`pages`](../apps/web/src/pages) implements Home, Search, Product, Basket, Index, Quality, Data, About and not-found states.
[`lib/basket.ts`](../apps/web/src/lib/basket.ts) persists only barcodes and quantities locally and synchronizes browser tabs.
[`BasketAssistant`](../apps/web/src/components/BasketAssistant.tsx), [`lib/ai-basket.ts`](../apps/web/src/lib/ai-basket.ts) and [`BasketSplit`](../apps/web/src/components/BasketSplit.tsx) keep proposal selection, budget totals and split comparisons visible to the shopper.
Storage restrictions can make the basket temporary, stale query data can need refresh, and model status or network failure can hide the assistant.

## Evaluation, benchmarks and quality gates

[`ai/evaluate.py`](../apps/api/src/korpa_api/ai/evaluate.py) matches extracted items against labeled phrases and optionally scores database candidates.
Recorded mode is a network-free smoke check; the separately retained live report is evidence of the dated provider run.
[`bench.py`](../apps/api/src/korpa_api/bench.py) and [`gql_bench.py`](../apps/api/src/korpa_api/gql_bench.py) support repeatable synthetic database measurements, which are not production latency promises.
The [CI workflow](../.github/workflows/ci.yml) checks schema drift, audits, lint/types/tests, migrations, build, browser flows and the Home budget.
[`scripts/lighthouse.mjs`](../apps/web/scripts/lighthouse.mjs) measures mobile pages with fixture responses and publishes reports separately from thresholds.
Fixture success cannot establish real publisher quality, model accuracy, live cold-start behavior or complete accessibility conformance.
Database tests require the dedicated `korpa_test` database; local skips must not be reported as integration passes.

## Twenty likely questions

1. **Why this project?** Public price files exist, but shoppers need comparable dated observations, complete baskets and visible data-quality limits.
2. **Why match by barcode?** It is a source identifier with exact text semantics; fuzzy names are used for search, not silently merging product identities.
3. **Why integer para?** It keeps money arithmetic exact; the web formats the integer only at display time.
4. **Why not reject every publisher variation?** Exact approved mappings recover useful data while counters expose each deviation; unapproved variants remain errors.
5. **What prevents a broken file from emptying the catalog?** Atomic writes, header/completeness checks, source-date checks and the suspicious-shrink guard limit withdrawals.
6. **What does a 304 mean for quality?** It represents the previously processed file, retaining its quality counts; it is not a new validation of changed rows.
7. **How does search handle Serbian?** Query transliteration and database-compatible normalization feed full-text/trigram matching, with explicit prefix and coverage ranking.
8. **Why REST and GraphQL?** REST gives bounded flat operations; GraphQL lets the product page choose nested relationships without a separate endpoint per shape.
9. **How is N+1 avoided?** Request-scoped loaders batch relationships and a shared-session lock serializes concurrent database access; integration tests check query counts.
10. **How do you limit GraphQL cost?** Depth, aliases, tokens, input/result caps and static cost reject excessive expansion before resolution.
11. **How do discounts work?** The shared effective-price expression applies a recorded discount inside inclusive date bounds; absent bounds are open.
12. **What does “cheapest basket” mean?** The lowest complete retail-format total for selected barcodes and quantities; incomplete totals remain labeled separately.
13. **Does the split minimize trips?** No: it chooses the lowest price per item with deterministic ties, then reports selected format count; travel and delivery are excluded.
14. **Why static JSON?** Overview routes remain usable while the API sleeps, at the cost of waiting for another export to refresh those observations.
15. **How is history kept within budget?** Daily detail expires, older format snapshots compact to product-month summaries, and storage guards stop writes before the configured cap.
16. **Is the index official inflation?** No: it is an unweighted fixed-base geometric mean of matched regular-price relatives with explicit exclusions and provisional current points.
17. **Why no vector database?** Existing search avoids extra embedding storage, memory and calls within the project's budget; ADR 0002 records the tradeoff.
18. **Can the model invent prices?** Its extraction cannot create displayed price facts; catalog retrieval and application arithmetic provide them, and notes are checked against supplied facts.
19. **What does the live evaluation prove?** The dated mixed-provider system achieved the report's metrics on the labeled named-product set; it does not score goal suitability or guarantee availability.
20. **What would you improve next?** Review the official Cyrillic/header compatibility gap, zero-price observations and source errors, then broaden evaluation before claiming general goal-planning quality.
