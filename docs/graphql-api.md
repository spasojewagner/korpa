# Read-only product graph

The endpoint is `/graphql` (GET or POST). It has no mutation or subscription type.
Introspection is enabled in every environment. Set `ENV=dev` before starting the API to
enable the interactive editor; otherwise a GET without a query returns 404.

Start the database, apply migrations and run the API as described in the README:

```sh
uv run --extra dev uvicorn korpa_api.main:app --reload
```

The same effective-price function serves both public APIs: a discounted amount applies
inside its inclusive discount interval, with missing bounds open. Dates use Belgrade's
current calendar day. Amounts are integer para. Select `listDate` with each displayed
price. Successful responses also carry `extensions.as_of`, even if the query omits
`asOf`; a current price exposes `asOf` as well. Monthly and daily history expose the
recorded regular/discounted amounts and their observation date as `listDate`. The stored
history has no discount-window columns, so it cannot reconstruct historical effective
prices.

```graphql
query ProductDetail($barcode: String!) {
  asOf
  product(barcode: $barcode) {
    barcode name brand unit
    category { code name }
    names { rawName retailer { name slug } }
    prices {
      format { id name retailer { name slug } }
      regularPara discountedPara effectivePara unitPricePara vat
      discountFrom discountTo listDate
    }
    cheapest { effectivePara listDate format { name } }
    history(months: 1) { month regularPara discountedPara listDate }
    changes(days: 1) { changedOn regularPara discountedPara listDate }
  }
}
```

```sh
curl http://127.0.0.1:8000/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"query($b:String!){product(barcode:$b){barcode prices{effectivePara listDate}}}","variables":{"b":"0000000000001"}}'
```

The other roots are `products(barcodes: [...])` and `categories { code name }`.
Products preserve the requested order, including duplicate positions; unknown barcodes
yield null. An existing product with no current listings has empty `prices` and null
`cheapest`. Cheapest ties resolve by format ID. Names/prices sort by retailer/format ID;
history sorts newest first, then by format ID.

## Bounds and errors

| Input or result | Bound |
|---|---|
| Barcode | Exactly thirteen digits, preserved as text |
| Products per root field | 1–50 |
| History window | 1–24 months, default 12, including the current month |
| Changes window | 1–120 days, default 30, including today |
| Current prices per product | 60 |
| Published names per product | 50 |
| History or changes per product | Smaller of window × 60 and 1,000 records |
| Document depth / aliases / tokens | 6 / 15 / 1,000 |
| Static query cost | At most 5,000 |
| JSON request / query text | 256,000 bytes / 64,000 characters |

Every selected field costs one. Children of a list multiply by its result cap; the
products list uses the supplied barcode count, up to fifty. Window arguments and
variable defaults determine history/changes caps. Aliases and fragment spreads are
counted; conditional directives do not reduce estimated cost. A broad query may need
fewer products or a narrower history selection even when each argument is individually
valid. For example, twenty products with prices → format → retailer name and one-month
history → month fit the budget. Adding more price fields can exceed it.

Limits reject the operation rather than silently truncating its data. In particular,
over sixty current formats cannot produce an incomplete cheapest comparison. For a
history result above its cap, request a narrower window. Future observations are excluded.

Errors use `application/problem+json` without partial GraphQL data: malformed JSON or
documents/limits return 400; invalid envelopes/arguments or oversized results return 422;
an oversized request body returns 413. Database failures return 503 with a generic
message; unexpected resolver failures return 500 without internal details. Successful
responses use the normal GraphQL data envelope. Successful GETs carry
`Cache-Control: public, max-age=300`.

## Schemas and typed clients

Use Node 22, the locked Python dependencies, and the package-manager version declared
in the root package manifest:

```sh
uv sync --extra dev --frozen
npm ci
npm ci --prefix apps/web
make schema
npm run codegen
npm --prefix apps/web run typecheck
```

Without Make, run the two export commands from its `schema` target. Schema export does
not need a running database. Commit the SDL, REST OpenAPI document and generated types
with every contract change. CI repeats both commands and fails on changed or untracked
artifacts. REST export includes all five HTTP paths and excludes the GraphQL transport.

The operation sources live in `apps/web/src/graphql/operations/`. Their typed documents
and helper live in `apps/web/src/gql/`; REST types live in `apps/web/src/api/rest.d.ts`.
The client preset is configured without fragment masking. Date scalars map to ISO strings,
unknown scalars fail generation, and operation helpers preserve strict unknown boundaries.
No frontend page or network client is added here.

## Verification and latency

```sh
export TEST_DATABASE_URL=postgresql+psycopg://korpa:korpa@localhost:5432/korpa_test
uv run --extra dev pytest
make lint
make test
make e2e
```

The batching regression test counts actual SQL statements: six for one product and six
for twenty, including prices → format → retailer and monthly history. It also changes a
price between requests to verify request-local caches. Separate cases cover each document
limit, invalid input shapes, inclusive discount boundaries, date windows, introspection,
editor visibility and explicit result-cap rejection.

Reproduce the HTTP benchmark in the dedicated synthetic database:

```sh
export DATABASE_URL=postgresql+psycopg://korpa:korpa@localhost:5432/korpa_bench
make seed-bench
uv run --extra dev python -m korpa_api.gql_bench
```

The seed command replaces only `korpa_bench`; the measurement command reads it and refuses
other database names. Results and the exact selection are in
[the latency report](bench/graphql-latency.json). It measures the complete loopback HTTP
response, fifty samples after ten warmups, over 12,000 products and 720,000 current prices
across sixty formats. The synthetic seed has no historical rows; populated history and
constant statement counts are covered by the integration test. These are local warm-data
measurements, not a hosted concurrency or production latency guarantee.

On 2026-11-21, p95 was 35.581 ms for one product and 205.819 ms for twenty;
medians were 24.672 ms and 163.580 ms respectively. The twenty-product query returns
1,200 nested current-format records.

There are no unresolved contract questions. Effective historical prices remain unavailable
because their discount-window provenance was never stored.
