# REST reads and normalized search

The API uses one async SQLAlchemy session and a read-only PostgreSQL transaction per request.
Apply migrations before starting it. The shared metadata remains in `korpa_ingest.db`.
Prices are integer para; price responses include `as_of`, and observations carry `list_date`.
The date is computed once per endpoint in Europe/Belgrade. Validation failures use RFC 9457
`application/problem+json`; database connection failures use 503 and unexpected failures 500
without returning internal diagnostics. Successful GET responses cache publicly for 300 seconds.

## Run locally

From the repository root, after the regular local dependency/database setup:

```sh
uv sync --extra dev --frozen
uv run --extra dev alembic -c apps/api/alembic.ini upgrade head
uv run --extra dev uvicorn korpa_api.main:app --reload
```

Set `DATABASE_URL` for the selected PostgreSQL database and `CORS_ORIGINS` to a comma-separated
origin list. `GET /health` remains available without a live database query. `/docs` and
`/openapi.json` describe the REST response models. The basket POST is a read, with no database
mutations; its origin preflight is allowed by the CORS configuration.

## Endpoints

```sh
curl --get http://127.0.0.1:8000/api/search --data-urlencode 'q=čokolada' --data 'limit=20&offset=0'
curl -X POST http://127.0.0.1:8000/api/basket -H 'Content-Type: application/json' -d '{"items":[{"barcode":"0000000000001","qty":2}]}'
curl http://127.0.0.1:8000/api/categories
curl http://127.0.0.1:8000/api/quality
```

The example barcode exists in the synthetic benchmark dataset; a live publisher's actual
barcode should be used against a live-data database.

- **Search:** `q` is 2–100 characters; optional category is 1–25; limit is 1–50 (default 20),
  offset 0–1000. Thirteen ASCII digits select only that exact barcode. Other queries are
  transliterated from Serbian Cyrillic, then normalized. Full-text OR word-trigram candidates
  rank by full-text rank plus similarity, then name and barcode. Price aggregation runs only
  for the selected page. Items contain `min_effective_para`, `max_effective_para`, `n_formats`,
  `any_discount`, and the newest `list_date`. Products must have at least one current price,
  including for exact barcode searches. Min/max prices and source date are non-nullable.
  `total` counts only matching products with current prices, including when an offset returns
  an empty page; retained catalog/history records alone cannot keep a withdrawn item visible.
- **Basket:** 1–50 input items, exact text barcodes and integer quantities 1–99. Duplicate
  barcodes merge; a merged quantity above 99 is rejected. Only formats with at least one
  requested barcode found appear; retailers with no matching formats are omitted. An entirely
  unavailable basket returns an empty retailer list. Genuine zero-priced matching products
  remain valid matches. Each row has a global `rank`, `complete`, `found_barcodes`, `missing_barcodes`,
  `total_para`, and `list_date_min`/`list_date_max`. Complete baskets rank first by total;
  partial baskets rank by number found, then partial total. Formats are nested under retailers;
  retailer groups appear in the order of their best-ranked format. The explicit completeness
  flag and global rank preserve honest comparison even when one retailer has both kinds.
  The response also includes `split`: the cheapest effective unit price for each requested
  barcode, multiplied by its merged quantity for `total_para`. Each entry in `items` has
  `barcode`, `format` (`id`, `name`), unit `price_para`, and `list_date`. Ties choose the format
  name then id, independently of database row order. `n_formats` counts the chosen formats;
  it does not optimize the number of stops and formats do not identify individual outlets.
  `saving_vs_best_para` compares the split total to the cheapest **complete single format**,
  and is null when no such format exists. The entire `split` is null when any requested
  barcode has no current price anywhere. Zero-priced items remain valid. Travel costs are
  excluded; the web card explains that buying across formats can mean visiting several stores.
- **Categories:** code, published name, and catalog product count, including empty categories.
- **Quality:** the latest ingest row per retailer, HTTP status, total/valid rows, errors,
  independent rule counts, deviations, profile, completion time, newest current list date,
  and days since that date. Status is `never` before any run, `ok` for a clean 200/304,
  `partial` for an error-bearing run with valid rows, and `failed` otherwise. A future source
  date produces a negative age instead of hiding that quality signal.

Effective price uses one shared SQL expression: discounted when present and both optional
date bounds include `as_of`, otherwise regular. Bounds are inclusive and absent bounds are
open. Basket multiplication promotes to bigint before multiplication; totals remain integers.

## Search storage and normalization

The migration enables `unaccent` and defines immutable `public.korpa_norm(text)` using lower,
`đ` → `dj`, and the explicit `public.unaccent` dictionary. The stored generated `search_norm`
column has a GIN trigram index. A trigger keeps `search_tsv` normalized on inserts and updates,
including future ingest writes that supply their own vector. The existing vector GIN index
is retained. `simple` tokenization is intentional: PostgreSQL has no built-in Serbian stemmer,
so guessing an unrelated language would damage Serbian matches.

The Python twin uses the verified 1,650-character PostgreSQL 16 unaccent mapping, packaged with
its source/license notice. Tests compare the complete mapping corpus and Serbian/Latin brand
words (including `Straße`, `Œuf`, `Łódź`) against the installed SQL function. Replacing the
PostgreSQL dictionary requires refreshing the table and parity checks together. Product names
and brands are returned as published; only queries and search-index columns are normalized.

`prices_current(barcode)` has its own B-tree index because the primary key begins with
`format_id`. Basket requested values are cast to CHAR(13), preserving the indexed price column's
type and enabling indexed barcode lookups.

Implementation references:
[async sessions](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html),
[unaccent](https://www.postgresql.org/docs/16/unaccent.html), and
[trigram indexes](https://www.postgresql.org/docs/16/pgtrgm.html).

## Tests and reproducible performance run

API integration tests accept only a dedicated `korpa_test` or `korpa_api_test` database.
CI uses its PostgreSQL service with `TEST_DATABASE_URL`; tests apply migrations and clear
their fixture tables. Do not point this setting at live data. Run:

```sh
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy
```

The benchmark CLI refuses any database not named `korpa_bench`, before migrating or seeding.
Its seed replaces synthetic data only in that dedicated database:

```sh
docker compose -f infra/docker-compose.yml exec -T db createdb -U korpa korpa_bench
export DATABASE_URL=postgresql+psycopg://korpa:korpa@localhost:5432/korpa_bench
make seed-bench
make bench
```

Without Make, run `uv run --extra dev python -m korpa_api.bench seed` and
`uv run --extra dev python -m korpa_api.bench measure`. In PowerShell set
`$env:DATABASE_URL='postgresql+psycopg://korpa:korpa@localhost:5432/korpa_bench'`.
The benchmark starts/stops its own local server on port 8765. It measures actual loopback HTTP,
including async sessions, database reads, response validation, and JSON serialization.

Observed locally on 21 November 2026 with 12,000 products, 60 formats, and 720,000 current
prices, after 10 warmups and 50 measured requests per endpoint:

| Request | Median | p95 |
| --- | ---: | ---: |
| Search (mixed exact spelling and typo queries) | 28.213 ms | **35.384 ms** |
| Basket with 20 distinct items | 11.431 ms | **14.518 ms** |

Both p95 values are below the 200 ms target. The synthetic database occupied 137,903,127 bytes.
These are local warm-cache measurements, not an external-network latency guarantee.

The complete [latency record](bench/rest-latency.json) and
[EXPLAIN ANALYZE plans](bench/search-explain.txt) are committed. The search count/page plans use
BitmapOr across the vector/trigram GIN indexes; page price summaries use the barcode index.
The actual 20-item basket query uses 20 barcode-index scans (60 rows each), not a scan of the
720k-row price table. Recorded SQL execution times were 11.211 ms for search count, 12.497 ms
for the page/price aggregation, and 0.710 ms for basket aggregation.

GraphQL and code generation remain a separate phase. No GraphQL endpoint is introduced here.
