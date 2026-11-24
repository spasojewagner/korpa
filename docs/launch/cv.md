# CV and LinkedIn copy — draft

Numbers below refer to the dated [README results](../../README.md#measured-results), not ongoing counters.
Use manually after reviewing the wording for the target role.

## CV bullets

- Built Korpa, a Serbian grocery comparison application with React/TypeScript, FastAPI and PostgreSQL, exposing dated REST, read-only GraphQL and MCP access.
- Implemented validation and atomic ingestion for 40 discovered publisher entries; the 2026-11-24 deployed quality snapshot represents 1,005,169 accepted source rows of 1,352,936 inspected rows (74.30%), including historical and duplicate records, not unique products.
- Designed bounded price-history storage, static overview exports, complete/partial basket comparison and a fixed-base Jevons index with explicit data exclusions.
- Added validated language-model extraction and catalog retrieval: the 2026-11-24 mixed Gemini/Groq live evaluation on 50 sentences measured 93.7% recall, 94.9% precision and 88.6% top-5 retrieval; mobile Lighthouse with mocked data measured performance 99–100 and accessibility 100 across five routes.

## LinkedIn description

Built Korpa, an independent open-data grocery comparison app for Serbia, connecting validated retailer CSV ingestion to dated product comparisons, basket totals, a monthly index and public read-only interfaces.
The project makes quality gaps visible and constrains model assistance to checked extraction and catalog-backed choices; its [case study](../../README.md) links the dated data snapshots, mixed-provider evaluation and fixture-based performance measurements.

Evidence: [quality snapshot](evidence/2026-11-24/quality.json),
[live report](../ai-eval/results-live.md) and [Lighthouse summary](evidence/2026-11-24/lighthouse-summary.json),
all dated 2026-11-24. No paid-service, official-affiliation or production-availability claim is implied.
