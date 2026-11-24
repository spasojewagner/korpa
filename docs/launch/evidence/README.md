# Evidence register — 2026-11-24

Repository baseline: `6eb264c3a2877ff23530dde057294df474903878` (`origin/main` at the start of this review).
PR #40 is merged at this commit; the earlier ingestion, analytics, design, basket split and performance/security
prerequisites are ancestors. Main's completed [CI](https://github.com/spasojewagner/korpa/actions/runs/45425688878)
and [deploy](https://github.com/spasojewagner/korpa/actions/runs/45425689023) succeeded.

## Static data check

The unchanged response bodies in [2026-11-24](2026-11-24) were fetched from
[quality](https://ai-korpa.vercel.app/data/quality.json),
[index](https://ai-korpa.vercel.app/data/index.json) and
[categories](https://ai-korpa.vercel.app/data/categories.json) on 2026-11-24.
Both dated responses say `as_of: 2026-11-24`; the individual quality entries retain their ingest finish times.
The [manifest](2026-11-24/manifest.json) records source URLs, SHA-256 and the subsequent evidence-copy timestamp
(not an exact network-response timestamp).

Recalculate the README counts by summing `retailers[*].rows_total` and `rows_valid`, grouping `status`, and
counting positive `rows_valid`. The accepted share is `100 * sum(rows_valid) / sum(rows_total)`, rounded to two
decimals. These are latest source-report counts, including monthly data and duplicate records, not distinct
products or a simultaneous successful full ingest. Zero-row download failures do not add unknown source rows
to the denominator. Check code 0's points in `index.json` for the exact index values and counts.

## Retailer and dataset check

[datasets.json](2026-11-24/datasets.json) preserves portal discovery metadata fetched with the existing
`PortalClient` on 2026-11-24. It is a discovery snapshot, not a license grant or claim of exhaustive coverage.
For example, actual discovered datasets include:

- [Lidl](https://data.gov.rs/api/1/datasets/68f61917f9daecc02d803b84/).
- [BRICO](https://data.gov.rs/api/1/datasets/6a329a1969e6025495f2d2b6/).
- [RIČ](https://data.gov.rs/api/1/datasets/6a95ed3adf0d645f96b6f3de/).

[retailer-observations.json](2026-11-24/retailer-observations.json) retains current resource URLs, exact decoded
headers, one row example, raw response hashes and read-only local parser reports for all seven failed entries.
Fresh downloads were unconditional HTTP 200s and passed through the unchanged `compat-2026-11.3` reader;
no database was accessed or updated. Each probe has a UTC timestamp, separate from the deployed ingest time.
Full CSV bodies are not redistributed here. The saved examples and hashes identify the evidence used for drafts.
Different row totals (notably Konovo) reflect a later source observation, not a correction to the quality snapshot.

## Legal/data-standard check

The [official consolidated rulebook](https://pravno-informacioni-sistem.rs/eli/rep/sgrs/ministarstva/pravilnik/2026/76/3/reg)
was read with JavaScript enabled on 2026-11-24. [Retained text](2026-11-24/official-standard.txt) includes its
legal basis (Consumer Protection Law article 6 paragraph 7, Gazette 35/26), amendments 76/2026 and 98/2026,
articles 2–5 and the technical annex. No universal retailer obligation or shop-level price promise is inferred.
Annex §4 has the logical columns; §5 describes values, §7 dates/prices/empty fields and §8 UTF-8 CSV checks.
The official Cyrillic text uses an en dash and Cyrillic unit/list-type values. Those can fail the current parser:
especially Statovac's header rejection must not be presented as a demonstrated standards breach.
Retailer emails cite observed export fields and ask for clarification rather than issuing legal conclusions.

## Evaluation check

[results-live.md](../../ai-eval/results-live.md), [live.jsonl](../../ai-eval/live.jsonl),
[verification.json](../../ai-eval/verification.json) and [failover-log.txt](../../ai-eval/failover-log.txt)
are byte-for-byte copies of the supplied successful-run evidence. Source:
[run 45417014920](https://github.com/spasojewagner/korpa/actions/runs/45417014920),
[artifact 14933583105](https://github.com/spasojewagner/korpa/actions/runs/45417014920/artifacts/14933583105),
2026-11-24, commit `8863481928925b9959f9ae5a3ad85da52590ed44`.
The manifest retains original-file hashes; the report remains unchanged, with this register providing provenance.
Checks verified 50 unique IDs matching the committed phrase set, 29 Gemini and 21 Groq responses, their exact
model names, 23 failover log lines and no HTTP 429. A network-free replay of the retained responses reproduces
the four extraction metrics. Top-1/top-5 are taken from the original database-enabled live report; the recording
does not contain candidate lists, so retrieval cannot be independently reconstructed from it alone.
No new live evaluation or model request was made for this documentation.

## Lighthouse check

Downloaded `lighthouse-reports` from completed successful [CI run 45411937189](https://github.com/spasojewagner/korpa/actions/runs/45411937189),
commit `8863481928925b9959f9ae5a3ad85da52590ed44`,
[artifact 14928091653](https://github.com/spasojewagner/korpa/actions/runs/45411937189/artifacts/14928091653).
Full JSON reports were inspected; [summary](2026-11-24/lighthouse-summary.json) retains report hashes,
`fetchTime`, requested URL, version and category scores. [Original score table](2026-11-24/lighthouse-scores.md)
also includes thresholds, which are distinct from the measured scores above them.
The runner uses mobile defaults, production build, mocked API/static responses and a populated fixture basket.
It is not a measurement of the deployed API or field users.

## Screenshot check

[Production screenshots](../../images/v1/provenance.json) retain URL, timestamp, viewport and capture context.
They use actual production responses, no intercepted fixture data, and make no model-generation request.
They show the deployed design, not reconstructed mockups. Source dates visible in the pages refer to the
underlying observations; the capture date does not refresh those prices.
