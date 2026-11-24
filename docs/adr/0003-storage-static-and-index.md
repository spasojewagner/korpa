# ADR 0003: Bounded storage, static overviews and checked analytics

Status: records the implemented v1 decisions, reviewed 2026-11-24 at `6eb264c`.
This records existing behavior; it introduces no runtime change or hosting-plan commitment.

## Money and storage

Prices are integer para, not binary floating-point currency. CSV parsing uses Decimal and exact conversion;
API response fields make the unit explicit and the web formats money only for display.
The configured database budget is 1 GB, warning at 70% and refusing/rolling back writes at 90%.
Daily changes retain 120 days; format-level monthly snapshots retain the last three months, with older
months compacted to per-product monthly min/median/max and minimum discount observations.
The combined history view preserves monthly reads, but older format detail is lost.
Raw CSVs are not stored in persistent database tables.

Source: [store.py](../../packages/ingest/src/korpa_ingest/store.py),
[database model](../../packages/ingest/src/korpa_ingest/db.py),
[reader](../../packages/ingest/src/korpa_ingest/reader.py), reviewed 2026-11-24.
The budget is project policy; it is not a verified current provider-plan entitlement.

## Static overviews

The free API can sleep. Export categories, quality, index and signals during deployment, so the overview routes
read static JSON first and use the API as fallback. Every export retains its source date; a working page can
still show stale data after a failed job. Search, products and baskets still depend on the API.
See [export_static.py](../../apps/api/src/korpa_api/export_static.py),
[web data access](../../apps/web/src/lib/api.ts) and [deployment](../deploy.md).

## Jevons index

Use the first observed monthly snapshot as fixed base = 100. For products present in both base and target,
take the lower observed median regular price across formats, then compute `100 × exp(mean(ln(target/base)))`.
Discounts are excluded. Nonpositive prices and relatives outside the inclusive [1/3, 3] interval are excluded
and counted; missing unmatched products are not exclusions. Publish only with at least 30 usable products.
Round stored/published values to four decimal places. The same rule over all products gives code 0.
Monthly snapshots, including the current month's first-day snapshot, are final; current-price points are
provisional, calculated on read with the full `as_of` date and never persisted as final history.
This avoids invented expenditure weights but gives no household spending or official inflation estimate.
Source: [analytics.py](../../apps/api/src/korpa_api/analytics.py), reviewed 2026-11-24.

## Checked index text

Optional model notes receive formatted index facts, not permission to invent causes or predictions.
The validator checks numeric tokens against declared-category facts, checks direction wording and rejects
banned causal/predictive words and Cyrillic output. Invalid sentences are dropped, not repaired.
This bounded filter can miss linguistic mistakes; it is not a general semantic proof.
Source: [notes.py](../../apps/api/src/korpa_api/ai/notes.py), reviewed 2026-11-24.
The basket extraction and no-embedding decision remain in [ADR 0002](0002-ai-without-embeddings.md).
