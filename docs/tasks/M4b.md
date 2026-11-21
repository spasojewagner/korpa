# Task: M4b (price index, unusual-change signals, category browsing)

Read `AGENTS.md`, `docs/ARCHITECTURE.md` and `docs/deploy.md` first. Backend work is split into three PRs
(A, B, C below), each into `main`, stop and report after each. The web pages for this task are built separately
against the contract in this file: do not change the JSON shapes without asking in the PR.

## Method (this text is shown to users; keep code and docs consistent with it)
- **Price per product and month** = median regular price across the retail formats that list it
  (`monthly_price_history.median_regular`). Discounts are excluded: the index tracks regular prices.
- **Category index** (Jevons, fixed base): base month = first month with data (now 2026-11) = 100.
  For month *m*, take products of the category present in the base month and in *m*; price relative
  r = P(m) / P(base); drop relatives outside [1/3, 3] as probable data errors (count them);
  index = 100 × exp(mean(ln r)). Publish only with ≥ 30 matched products, otherwise `value: null`.
- **Overall index**: same formula over all products, reported as category code `0`, name "Sve kategorije".
- **Provisional point** for the current month: same formula with P = median of `prices_current.regular`
  for the product on `as_of`, flagged `provisional: true`. It is computed on read, never stored.
- **Signals** are prompts for review, never accusations; each carries the rule that produced it.
  - `jump`: a format's regular price rose ≥ 25 % against that format's previous regular price for the same
    product (consecutive `price_changes` rows) within the last 30 days.
  - `outlier`: a format's current effective price is ≥ 1.5 × the median current effective price of the same
    product in at least 3 other formats.

## Contract
Static files written by `export_static` next to `categories.json` and `quality.json`, and identical REST
responses (`GET /api/index`, `GET /api/signals`). Money in para, dates ISO.

```jsonc
// index.json  ==  GET /api/index
{
  "as_of": "2026-12-02",
  "base_month": "2026-11-01",
  "categories": [
    {
      "code": 0, "name": "Sve kategorije",
      "points": [
        { "month": "2026-11-01", "value": 100.0, "n_products": 61234, "n_excluded": 0, "provisional": false },
        { "month": "2026-12-01", "value": 101.4, "n_products": 59876, "n_excluded": 12, "provisional": true }
      ]
    }
  ]
}
// signals.json  ==  GET /api/signals?type=jump|outlier&limit=1..200 (default 100, newest first)
{
  "as_of": "2026-12-02",
  "items": [
    {
      "type": "jump", "barcode": "8600000000001", "name": "Mleko 2,8% 1 l",
      "retailer": "Alfa", "format": "Alfa Hiper", "date": "2026-12-01",
      "price_para": 18999, "reference_para": 14999, "ratio": 1.27
    }
  ]
}
```
For `jump`, `reference_para` is the previous regular price and `date` the change date; for `outlier` it is the
median of the other formats and `date` the format's list date. `ratio` = price / reference, 2 decimals.

## A — Index (Codex)
1. `korpa_api/analytics.py`: compute the index exactly as above from `monthly_price_history` and
   `prices_current`; write completed months into `index_monthly` (upsert; `value` NULL allowed when below the
   threshold — add a migration if the column is NOT NULL). Run it at the end of `korpa ingest` after compaction.
2. `GET /api/index` and `index.json` in `export_static` (same shape). Pydantic schemas, problem+json, caps.
3. Tests with synthetic data: base = 100, a known 10 % rise gives 110.0, relatives outside [1/3, 3] excluded and
   counted, < 30 products gives `null`, provisional flag, overall code 0. Export matches REST (like the existing test).

## B — Signals (Codex)
4. Both rules as SQL in `analytics.py`; `GET /api/signals` with `type` and `limit`; `signals.json` (limit 200).
5. Tests: exact thresholds (24.9 % no, 25 % yes; 1.49× no, 1.5× yes), fewer than 3 other formats → no outlier,
   30-day window edge, ordering. Report on live data: counts per type and per retailer in the PR, not in the repo.

## C — Category browsing and data report (Codex)
6. `/api/search`: `q` becomes optional when `category` is given (at least one of them is required);
   without `q`, order by number of formats desc, then name. Tests, OpenAPI, `npm run codegen`.
7. `docs/data-notes.md`: for each of the 8 retailers with status `failed` on `/kvalitet`, the exact cause
   (header line, encoding, download error) and a proposal. Do not add mappings: the maintainer decides.

## Web (done separately)
`/indeks`: overall and per-category lines with a table alternative, base month and method in plain words,
signals list with the rule for each item. Home: categories grid linking to category browsing.

## Done when
All gates green, `index.json` and `signals.json` published by the nightly workflow, REST equals static files,
p95 of `/api/index` and `/api/signals` under 200 ms on the bench DB.
