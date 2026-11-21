# Task: M4b (price index, unusual-change signals, category browsing)

Read `AGENTS.md`, `docs/ARCHITECTURE.md` and `docs/deploy.md` first. Backend work is split into three PRs
(A, B, C below), each into `main`, stop and report after each. The web pages for this task are built separately
against the contract in this file: do not change the JSON shapes without asking in the PR.

## Method (this text is shown to users; keep code and docs consistent with it)
- **Price per product and month** = median regular price across the retail formats that list it
  (`monthly_price_history.median_regular`). Discounts are excluded: the index tracks regular prices.
- **Category index** (Jevons, fixed base): base month = first month with data (currently 2026-09) = 100.
  For month *m*, take products of the category present in the base month and in *m*; price relative
  r = P(m) / P(base); drop relatives outside [1/3, 3] as probable data errors (count them);
  index = 100 × exp(mean(ln r)). Publish only with ≥ 30 matched products, otherwise `value: null`.
- Match only products present in both the base month and month *m* (an inner join).
  Missing products are unmatched and count in neither `n_products` nor `n_excluded`.
  Among matched products, a zero median in either month makes the relative undefined;
  exclude and count it in `n_excluded`, together with relatives outside [1/3, 3].
- Final monthly observations include every snapshot with month <= the current month's first
  day. A `MESEČNI_PRESEK` taken on the 1st is final even in the current calendar month.
- `n_products` is the number of products whose relative enters the mean, after all exclusions.
  The ≥ 30 threshold applies to `n_products`; below it `value` is null, while both counts
  are still reported. These same rules apply to the provisional point and overall code `0`.
- **Overall index**: same formula over all products, reported as category code `0`, name "Sve kategorije".
- **Provisional point** for the current month: same formula with P = median of `prices_current.regular`
  for the product on `as_of`, flagged `provisional: true`, with `month` equal to the full
  `as_of` date. It is computed on read, never stored, and follows the current month's final
  snapshot when one exists. On the 1st, both dates can match; the final point comes first.
- Index values are rounded to four decimal places. Before any monthly history exists, `base_month` is the
  current month's first day and all points are unpublished (`value: null`); without matched
  products both counts are zero. Categories are ordered by code,
  including overall `0` first; points are ordered by month and have one current provisional point.
- **Signals** are prompts for review, never accusations; each carries the rule that produced it.
  - `jump`: a format's regular price rose ≥ 25 % against that format's previous regular price for the same
    product (consecutive `price_changes` rows), with price / previous <= 3,
    within the last 30 days, including both
    `as_of - 30 days` and `as_of`; the preceding observation may be older than the window.
  - `outlier`: a format's current effective price is ≥ 1.5 × the median current effective price of the same
    product in at least 3 other formats, with price / median <= 3.
    The format being checked is excluded from its reference.
  - Effective prices use discounts active on `as_of` (inclusive start/end). Future-dated lists
    and changes are ignored. Medians follow the existing discrete convention (lower middle
    observed price for even counts). Ratios require a positive reference; zero references
    produce no signal. Apply thresholds before rounding the ratio to two decimals.
  - Both upper bounds are inclusive, matching the index's [1/3, 3] trimming. Compare integer
    prices by cross-multiplication before rounding. Candidates above 3 are probable data errors:
    exclude them from signals and count each rule candidate per retailer under
    `suspected_errors.price_outlier` in `/api/quality` and `quality.json` (empty object when none).
    Existing validation errors, deviations and status are unchanged.
  - Order date descending, then unrounded ratio descending, then barcode ascending; remaining
    ties use type and format id ascending for stable limits.

## Contract
Static files written by `export_static` next to `categories.json` and `quality.json`, and identical REST
responses (`GET /api/index`, `GET /api/signals`). Money in para, dates ISO. The export refreshes
final indices before reading, so a deployment without ingestion also publishes final snapshots.

```jsonc
// index.json  ==  GET /api/index
{
  "as_of": "2026-11-21",
  "base_month": "2026-09-01",
  "categories": [
    {
      "code": 0, "name": "Sve kategorije",
      "points": [
        { "month": "2026-09-01", "value": 100.0, "n_products": 61234, "n_excluded": 0, "provisional": false },
        { "month": "2026-10-01", "value": 100.7, "n_products": 60000, "n_excluded": 10, "provisional": false },
        { "month": "2026-11-01", "value": 101.0, "n_products": 60000, "n_excluded": 10, "provisional": false },
        { "month": "2026-11-21", "value": 101.4, "n_products": 59876, "n_excluded": 12, "provisional": true }
      ]
    }
  ]
}
// signals.json == GET /api/signals?limit=200
// REST also accepts type=jump|outlier and limit=1..200 (default 100), newest first.
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
