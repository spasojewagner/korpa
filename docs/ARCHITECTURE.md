# Korpa — architecture and roadmap

## 1. Problem and data
Serbia's Consumer Protection Law requires retailers to publish price lists as UTF-8 CSV files on the national open
data portal, following a technical standard (15 columns, see `AGENTS.md`). The official platform lists 11,750+
products across 39+ chains and 4,000+ outlets, but it is hard to compare prices with it. Korpa builds a fast, accessible
comparison layer on top of the same open data and reports data quality back in the open.

Key properties of the data:
- One consolidated CSV per retailer, stable file name, replaced on every price change.
- No store ID: the finest location unit is `Naziv trgovca - formata` (retailer + store format).
- Mandatory 13-digit barcode → products are matched by barcode, not by fuzzy names.
- A permanent `MESEČNI_PRESEK` (monthly snapshot) on the 1st of each month → real price history.

Open questions, answered in M1 and recorded in `docs/data-notes.md`: portal API shape for listing retailer datasets,
resource URLs, ETag / Last-Modified support, data license and attribution text.

## 2. Architecture

```
GitHub Actions (nightly cron + manual)
  └─ korpa ingest:
       portal API → download CSVs (conditional GET) → detect delimiter → validate 15 columns
       → normalize → upsert into Postgres → data-quality report
       → build static JSON (index, categories, quality) → publish to the static host
                                │
                                ▼
Neon Postgres (pg_trgm; pgvector from M5) ◀── FastAPI on Render
                                │              REST: /api/search, /api/basket, /api/categories, /api/quality
                                │              GraphQL: /graphql (read-only, nested product → prices → history)
                                │              MCP: /mcp (M5)
                                ▼
React + Vite + TS (static host) — reads static JSON first, calls the API only for search, product and basket
```

Free-tier constraints and how the design handles them:
- **Neon Free: 1 GB per project.** Writes fail above the cap → storage budget (section 4).
- **Render free web services sleep after 15 min idle (~1 min wake-up).** Home, index and quality pages are served from
  static JSON built nightly, so the first visit never waits for the API.
- **GitHub Actions** runs the nightly ingest for free on a public repo; no Redis or worker service needed.

## 3. Data model

| Table | Columns | Notes |
|---|---|---|
| `retailers` | id, name, slug, dataset_id, resource_url, last_etag, last_modified, validator_profile, last_seen_at | one per publisher |
| `retail_formats` | id, retailer_id, name | from `Naziv trgovca - formata` |
| `categories` | code (1–25), name | |
| `products` | barcode CHAR(13) PK, name, brand, unit, category_code, search_tsv | canonical name per barcode |
| `product_names` | barcode, retailer_id, raw_name | names as each retailer writes them |
| `prices_current` | format_id, barcode, regular, discounted, disc_from, disc_to, unit_price, vat, list_date, updated_at | PK (format_id, barcode) |
| `price_changes` | format_id, barcode, changed_on, regular, discounted | appended only when a price changes |
| `monthly_snapshots` | format_id, barcode, month, regular, discounted | from `MESEČNI_PRESEK`; last 3 months only |
| `monthly_prices` | barcode, month, min/median/max regular, min discounted, n_formats | older months, one row per product |
| `monthly_price_history` (view) | same columns | `monthly_prices` + live months aggregated; read by GraphQL `monthlyPrices` |
| `ingest_runs` | id, retailer_id, started_at, finished_at, http_status, rows_total, rows_valid, errors_json | one per retailer per run |
| `index_monthly` | month, category_code, value, n_products | materialized category index |

Money is INTEGER para (×100); dates are DATE.

## 4. Storage budget (1 GB)
- `price_changes` keeps 120 days; older history comes from `monthly_snapshots` (3 months per format) and
  `monthly_prices` (one row per product per month, kept forever: about 10× smaller than per-format rows).
- No raw CSVs in the database (raw files are kept 7 days as CI artifacts).
- `pg_database_size` is logged after every ingest: warn at 70 %, stop writing at 90 %.
- Estimate to verify in M1: ~12k products × ~60 formats ≈ up to 700k `prices_current` rows (order of 100–200 MB with indexes).

## 5. Frontend principles
Civic-tech clarity: mobile first, large readable type, tabular numerals for prices, color only with text ("najjeftinije"),
Latin/Cyrillic toggle, every number with its source date, designed empty/loading/error states, WCAG 2.2 AA,
home page under 100 KB JS and LCP under 2.5 s on 4G.
Pages: Home, Search results, Product, Basket, Price index, Data quality, About & sources.

## 6. Roadmap

| Phase | Scope | Done when |
|---|---|---|
| M0 Setup | monorepo, Docker Compose, Alembic, Makefile, CI | CI green, `make dev` works |
| M1 Ingest | portal spike, CSV reader + validator, normalizer, upsert, `ingest_runs`, CLI | real data from ≥ 5 retailers locally + quality report |
| M2 API | REST (search with pg_trgm + tsvector, diacritics-insensitive; basket; categories; quality) + read-only GraphQL with DataLoaders and limits | OpenAPI + GraphQL schema, tests, < 200 ms locally |
| M3 Web | design system, all pages, basket in localStorage, Latin/Cyrillic | Lighthouse ≥ 90 perf / 100 a11y, Playwright flows + axe pass |
| M4 Analytics + deploy | category index, unusual-change signals, static JSON, Neon + Render + nightly cron | live site with that morning's data |
| M5 AI | basket from a sentence (tool calling + pgvector), grounded index explanations, MCP server, eval on 50 labeled phrases | matching accuracy measured and published |
| M6 Launch | README case study, demo video, submit as a reuse example on the open data portal | published |

"Unusual change" items are always labeled as signals for review, never as violations, with the method explained.
