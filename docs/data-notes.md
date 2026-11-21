# Portal discovery and contract observations

Observed on 21 November 2026. These are observations of published files, not findings of legal
non-compliance. The repository's CSV contract remains authoritative for validation.

## Verified discovery interface

The portal exposes a public udata JSON API. No credentials were required:

- https://data.gov.rs/api/1/datasets/?q=cenovnici&page_size=5
- https://data.gov.rs/api/1/datasets/?q=cenovnici&page_size=5&page=2
- https://data.gov.rs/api/1/datasets/?q=pravilniku&page_size=100
- https://data.gov.rs/api/1/datasets/?q=%D1%86%D0%B5%D0%BD%D0%BE%D0%B2%D0%BD%D0%B8%D1%86%D0%B8&page_size=100
- https://data.gov.rs/api/1/datasets/?q=cenovnik&page_size=100

The response contains `data`, `next_page`, `page`, `page_size`, `previous_page`, and `total`.
Each dataset has `id`, `slug`, `organization` (`name`, `slug`), `license`, and `resources`.
Resources have `id`, `format`, `title`, `url`, and `latest`. The client follows `next_page`,
deduplicates dataset IDs, and only follows pagination on the configured portal origin.

Search is sensitive to script and inflection: `cenovnici` returned 6 datasets, `pravilniku` 1,
`ценовници` 41, and `cenovnik` 28. The three price-list searches together selected 40 publishers
with an unambiguous consolidated CSV name. This is an observed discovery heuristic, not a claim
of exhaustive grocery coverage. Unrecognized resource names remain a discovery limitation.

Resources are not uniformly portal-hosted. They include timestamped portal URLs, stable retailer
URLs, public blob URLs, and other remote hosts. Use the current dataset metadata on every run;
do not construct a download URL from the dataset ID or assume the upload directory is stable.
`latest` also exists, but its redirect/cache behavior was not used as a contract.

Some datasets contain many resources. Lidl's first CSV is an EAN mapping, not its price list:
https://data.gov.rs/api/1/datasets/68f61917f9daecc02d803b84/
The adapter selects CSV resources whose URL contains `cene_proizvoda` or `cene-proizvoda`.
Distinct matching resources or datasets for one publisher are reported as ambiguous, never chosen
by arbitrary ordering. Historical files with unrecognized names are not automatically imported.

## Previous compatibility profile `compat-2026-11`

The earlier CLI selected this profile; the current CLI uses `compat-2026-11.2` described below.
`read_csv` without a profile still provides
strict contract validation. No barcode, product text, price, date, or empty field is repaired.

Exact value mappings:

| Field | Source | Canonical | Deviation counter |
| --- | --- | --- | --- |
| VRSTA_CENOVNIKA | `MESECNI_PRESEK` | `MESEČNI_PRESEK` | `list_type_ascii` |
| VRSTA_CENOVNIKA | `VAZECI_CENOVNIK` | `VAŽEĆI_CENOVNIK` | `list_type_ascii` |
| Jedinica mere | ASCII case-insensitive exact `kg`, `g`, `l`, `ml`, `kom`, `pak` | lowercase unit | `unit_case` |

No other aliases are accepted: `kom.`, `lit`, `GR`, `JED`, `KO`, `M`, padded values, and
unlisted list types remain errors. Canonical values do not increase deviation counters.

### Lidl's observed header and explicit header aliases

Exact decoded first line (the file is UTF-8 and uses semicolons):

```text
KATEGORIJA;NAZIV KATEGORIJE;Naziv proizvoda;Robna marka;Barkod proizvoda;Jedinica mere;Naziv trgovca – formata;Datum cenovnika;Redovna cena;Cena po jedinici mere;Snižena cena;Datum početka sniženja;Datum kraja sniženja;Stopa PDV;VRSTA_CENOVNIKA
```

Lidl's en dash in column 7 is the sole non-identity header alias. It maps one-to-one; the file
can be accepted. Header cells are whitespace-trimmed and matched only through this table.
Column order may differ, but every canonical column must occur exactly once. Missing,
duplicate, additional, or unknown columns reject the entire file. A noncanonical accepted
header (alias, whitespace, or reordered columns) increments `header_alias` once per file.

| Accepted header after trimming | Canonical column |
| --- | --- |
| `KATEGORIJA` | `KATEGORIJA` |
| `NAZIV KATEGORIJE` | `NAZIV KATEGORIJE` |
| `Naziv proizvoda` | `Naziv proizvoda` |
| `Robna marka` | `Robna marka` |
| `Barkod proizvoda` | `Barkod proizvoda` |
| `Jedinica mere` | `Jedinica mere` |
| `Naziv trgovca - formata` | `Naziv trgovca - formata` |
| `Naziv trgovca – formata` | `Naziv trgovca - formata` |
| `Datum cenovnika` | `Datum cenovnika` |
| `Redovna cena` | `Redovna cena` |
| `Cena po jedinici mere` | `Cena po jedinici mere` |
| `Snižena cena` | `Snižena cena` |
| `Datum početka sniženja` | `Datum početka sniženja` |
| `Datum kraja sniženja` | `Datum kraja sniženja` |
| `Stopa PDV` | `Stopa PDV` |
| `VRSTA_CENOVNIKA` | `VRSTA_CENOVNIKA` |

Every applied value mapping is counted, including mappings on rows that fail another rule.
`errors` retains the first failing rule per invalid row for backward compatibility;
`errors_by_rule` counts each independently failing rule once per row, so it may sum to more
than the number of rejected rows. Dependent comparisons run only when their input fields
parse successfully. Deviations alone never invalidate a row. A new mapping needs a new
profile identifier and a maintainer decision.

## Five live downloads and local ingest reports

Re-run on 21 November 2026 with `compat-2026-11`. Full exact dataset/resource URLs, SHA-256
hashes, response validators, download sizes, rule counts, and timings are retained in
[portal-observations.json](portal-observations.json). All five files were downloaded, fully
processed, and imported into a fresh local PostgreSQL 16 database. Raw CSVs were not committed
or stored in persistent database tables; COPY stages contain only validated normalized rows.

| Publisher slug | Source records | Accepted | Deviations | Errors (first failing rule) |
| --- | ---: | ---: | --- | --- |
| `beltorg-doo-1` | 2,075 | 1,799 | list_type_ascii: 2,075 | conflicting_duplicate: 276 |
| `lidl` | 12,628 | 9,781 | list_type_ascii: 12,628; header_alias: 1 | unit: 2,684; price: 84; conflicting_duplicate: 79 |
| `luki-komerc-d-o-o` | 25,181 | 24,990 | list_type_ascii: 25,181 | unit: 76; price: 97; conflicting_duplicate: 18 |
| `metro-cash-carry-doo-beograd` | 38,039 | 20,372 | list_type_ascii: 38,039; unit_case: 33,770 | price: 13,292; unit: 4,269; conflicting_duplicate: 106 |
| `yuhor-d-o-o` | 4,612 | 4,268 | list_type_ascii: 4,612 | price: 312; conflicting_duplicate: 32 |
| **Total** | **82,535** | **61,210** | **116,306 applied mappings** | **21,325 rejected records** |

These are source-record counts, not distinct current listings. Exact duplicates remain valid
source records but collapse to one write; conflicting duplicate identities are all rejected.
Current listings after the imports: Beltorg 667, Lidl 2,466, Luki 6,318, Metro 5,077, Yuhor 1,080.
All five publishers now have usable current prices and retained monthly observations.

The extra rule report exposes masked failures: Metro has 16,593 `price` failures and 4,269
`unit` failures, in addition to 106 conflicting records; Lidl has 99 `price` failures rather
than the first-error count of 84; Luki has 113 rather than 97. Prices such as `100` or `1000.1`
remain errors because only exact two-decimal prices were approved. These quality signals do
not establish legal non-compliance.

Four resource servers supplied Last-Modified; Luki, Metro, and Yuhor also supplied ETag.
Actual conditional requests returned **304** for all four; Lidl supplied neither validator.
The client prefers If-None-Match, otherwise If-Modified-Since. Validators are stored after an
accepted header and complete processing even when individual rows fail. They are bound to
both the exact source URL and parsing profile; a profile change forces a new full download.
Rejected headers, malformed CSVs, and encoding/download errors cannot refresh the cache.
A 304 retains the previous file's totals, quality counters, validators, and shrink baseline;
it does not rerun writes or withdrawals.

The five datasets declare `license: sodl`. The verified portal registry identifies it as
`Српска лиценца за отворене податке`, maintained by ITE, with a null license URL:
https://data.gov.rs/api/1/datasets/licenses/
The full license text and attribution wording still need review before public redistribution.
The app links the portal and displays the required independence disclaimer; it does not assume
a single license applies to every resource.

## Atomic writes, withdrawals, and storage

The writer uses COPY into a transaction-local temporary table followed by a fixed number of
INSERT ... SELECT ... ON CONFLICT statements. Canonical descriptions remain first seen;
retailer product names update from the latest source observation. Money remains integer para.
Intra-file price changes are compared with window functions before the current-price upsert.
Older lists cannot revert newer prices. Monthly observations remain immutable.

An accepted, fully processed file containing current-list rows replaces this retailer's
current listings: absent valid current `(format, barcode)` keys are withdrawn. Monthly-only,
rejected-header, truncated, and 304 responses cannot withdraw listings. A stale source cannot
delete listings newer than the source's latest current date. Other retailers and historical
observations are unaffected by withdrawal.

Before replacement, `rows_valid` is compared to the previous fully processed accepted run's
count. Below 50% triggers `suspicious_shrink`; current prices and their history are left
unchanged, and no withdrawals occur. Exactly 50% is allowed. Shrink rejections and rejected
files do not reset the baseline, so repeated suspicious files cannot bypass the guard.
304 audits retain the represented file's counts. Monthly snapshots can still be imported
from a suspicious mixed file without changing current prices.

Publisher writes are atomic and serialized through transaction advisory locks. Database size
is logged before/after import, warned at 70% of 1 GB, and the transaction is rejected/rolled
back at 90%. The independent 120-day daily-history retention policy remains active; monthly
observations are retained permanently. No raw CSV is stored in persistent tables.

## Performance measurement

Local Docker PostgreSQL 16, sequential imports, same machine and the same Metro bytes
(SHA-256 in the observation file). Both isolated Metro comparisons started without product,
current-price, or history data. The original database retained the five retailer records and
rejected-run audit metadata from the strict-only spike; the bulk comparison used a fresh
database. Network time is excluded from both Metro parse/write comparisons. The old writer was taken
from commit `e4832ed6349dfcfade8e63c4bd52131625c8c9f0` and fed the same approved-profile rows.

| Measurement | Original per-row writer | COPY and set-based writer |
| --- | ---: | ---: |
| Metro source records / accepted | 38,039 / 20,372 | 38,039 / 20,372 |
| Metro parsing + normalization | 1.364 s | 0.775 s |
| Metro transaction | 40.891 s | 3.894 s |
| Metro total parse + write | **42.255 s** | **4.668 s** |

The complete fresh-database five-retailer run took **18.690 s**, including **0.850 s** discovery,
all sequential downloads, parsing, writes, retention, and audits. This meets the local 60 s
target. Conditional support probes were performed after the timed run. No previously stored
HTTP validators were supplied and no files were skipped. Metro in that shared five-retailer
run took 1.869 s for parsing/writing because earlier chains had already populated some shared
products; that figure is not used as the isolated cold comparison.

These are observed local wall times, not a network latency guarantee. The larger forecast of
700k current rows remains a separate scale benchmark. Scheduled ingestion, raw-download
artifact retention, static JSON exports, product APIs, and deployment belong to later phases.

## Measured price/unit failures before `compat-2026-11.2`

Measured from fresh live downloads on 21 November 2026 before enabling the new mappings.
Counts inspect every field of every structurally valid source row under `compat-2026-11`,
including rows that also fail a different rule. Empty optional discounted prices are excluded;
empty required prices are `other`. These are field counts, not rejected-row counts.

| Retailer | Price column | Integer (`100`) | One decimal (`1000.1`) | >2 decimals | Comma decimal | Other |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `beltorg-doo-1` | Redovna cena | 0 | 0 | 0 | 0 | 0 |
| `beltorg-doo-1` | Cena po jedinici mere | 0 | 0 | 0 | 0 | 0 |
| `beltorg-doo-1` | Snižena cena | 0 | 0 | 0 | 0 | 0 |
| `lidl` | Redovna cena | 0 | 0 | 0 | 0 | 99 |
| `lidl` | Cena po jedinici mere | 0 | 0 | 0 | 0 | 99 |
| `lidl` | Snižena cena | 0 | 0 | 0 | 0 | 0 |
| `luki-komerc-d-o-o` | Redovna cena | 0 | 0 | 0 | 0 | 0 |
| `luki-komerc-d-o-o` | Cena po jedinici mere | 0 | 0 | 0 | 0 | 113 |
| `luki-komerc-d-o-o` | Snižena cena | 0 | 0 | 0 | 0 | 0 |
| `metro-cash-carry-doo-beograd` | Redovna cena | 10022 | 1461 | 0 | 0 | 0 |
| `metro-cash-carry-doo-beograd` | Cena po jedinici mere | 4697 | 2992 | 0 | 0 | 2360 |
| `metro-cash-carry-doo-beograd` | Snižena cena | 756 | 4 | 0 | 0 | 0 |
| `yuhor-d-o-o` | Redovna cena | 0 | 0 | 0 | 0 | 153 |
| `yuhor-d-o-o` | Cena po jedinici mere | 0 | 0 | 0 | 0 | 312 |
| `yuhor-d-o-o` | Snižena cena | 0 | 0 | 0 | 0 | 0 |

Unit failures under the previous profile, grouped by the exact published value:

| Retailer | Exact unit value | Count |
| --- | --- | ---: |
| `beltorg-doo-1` | — (none) | 0 |
| `lidl` | `kom.` | 2556 |
| `lidl` | `listić` | 36 |
| `lidl` | `br.pranja` | 84 |
| `lidl` | `m` | 8 |
| `luki-komerc-d-o-o` | `lit` | 20 |
| `luki-komerc-d-o-o` | `set` | 28 |
| `luki-komerc-d-o-o` | `dzak` | 24 |
| `luki-komerc-d-o-o` | `par` | 4 |
| `metro-cash-carry-doo-beograd` | `"" (empty)` | 2272 |
| `metro-cash-carry-doo-beograd` | `KO` | 1848 |
| `metro-cash-carry-doo-beograd` | `M` | 101 |
| `metro-cash-carry-doo-beograd` | `GR` | 44 |
| `metro-cash-carry-doo-beograd` | `JED` | 4 |
| `yuhor-d-o-o` | — (none) | 0 |

The frequent unapproved price shapes are empty required values (Lidl: 99 in each of regular
and unit-price columns; Luki: 113 unit prices; Metro: 2,272 unit prices; Yuhor: 153 regular
and 312 unit prices) and 88 leading-dot Metro unit prices such as `.18` and `.3`.
Leading-dot fractions are not mapped. No >2-decimal or comma-decimal failures were observed.
Unapproved units include `listić`, `br.pranja`, `m`, `set`, `dzak`, `par`, empty strings,
`KO`, `M`, and `JED`; these remain errors.

## Active profile `compat-2026-11.2`

The current CLI profile inherits the exact list-type and header mappings documented above.
It adds only:

| Field | Accepted source shape | Canonical representation | Deviation |
| --- | --- | --- | --- |
| Price | ASCII digits, no decimal (`100`) | `100.00` | `price_decimals` per field |
| Price | ASCII digits, dot, one decimal (`1000.1`) | `1000.10` | `price_decimals` per field |
| Unit | Exact ASCII case-insensitive `kom.` | `kom` | `unit_alias` |
| Unit | Exact ASCII case-insensitive `gr` | `g` | `unit_alias` |
| Unit | Exact ASCII case-insensitive `lit` | `l` | `unit_alias` |

Padding is exact; it never rounds. More than two decimals, commas, spaces, signs, thousands
separators, leading-dot fractions, and out-of-range integer para still fail `price`.
Unknown units still fail `unit`. Canonical two-decimal prices are not counted as deviations.
The previous profile remains available explicitly to the Python reader, with unchanged rules.
The stored validator profile must equal the active profile, so upgrading from `compat-2026-11`
forces a full GET even when ETag or Last-Modified was saved for an otherwise identical URL.
The five-file re-run below explicitly verified that old-profile validators were ignored.

### Five-file re-run with `compat-2026-11.2`

All five requests were full HTTP 200 responses: the saved previous-profile validators were
ignored by the existing validator mechanism. Sources changed since the earlier observation
(Luki now has 25,190 rows and Metro 38,041); the before/after valid counts below use the same
fresh bytes measured before this profile change. This re-run reused the local database and
took **101.8949 seconds**, including discovery, network downloads and database work.
This is a new observation, not a replacement for the earlier isolated writer benchmark.

| Retailer | Rows | Valid (previous profile, same bytes) | Valid (new profile) | Deviations | Errors (first failing rule) |
| --- | ---: | ---: | ---: | --- | --- |
| `beltorg-doo-1` | 2,075 | 1,799 | 1,799 | list_type_ascii: 2,075 | conflicting_duplicate: 276 |
| `lidl` | 12,628 | 9,781 | 11,970 | header_alias: 1; list_type_ascii: 12,628; unit_alias: 2,556 | unit: 128; price: 99; conflicting_duplicate: 431 |
| `luki-komerc-d-o-o` | 25,190 | 24,999 | 25,019 | list_type_ascii: 25,190; unit_alias: 20 | price: 97; unit: 56; conflicting_duplicate: 18 |
| `metro-cash-carry-doo-beograd` | 38,041 | 20,372 | 33,617 | list_type_ascii: 38,041; unit_case: 33,772; price_decimals: 19,932; unit_alias: 44 | unit: 4,225; price: 72; discount: 1; conflicting_duplicate: 126 |
| `yuhor-d-o-o` | 4,612 | 4,268 | 4,268 | list_type_ascii: 4,612 | price: 312; conflicting_duplicate: 32 |

Total: **76,673 valid records of 82,546**, compared with **61,219**
under the previous profile on those same measured bytes. Counts include valid duplicate source
records before identical duplicates collapse to database writes. New accepted rows can expose
conflicting duplicate identities, so the conflict count can increase after an alias is enabled.
Metro now also exposes one invalid discount; it remains an error. The report retains every
independent failing rule: for example, Metro still has 2,360 price failures even though only
72 are its first failing rule.

[profile-2-observations.json](profile-2-observations.json) contains all measurements, exact
source URLs, hashes, both profiles, the fresh-read proof, deviations, and independent rule counts.

## Eight failed retailers: observed causes and proposals

Investigated on 21 November 2026. The set is the eight `status: failed` publishers in
[the static quality response](https://ai-korpa.vercel.app/data/quality.json) used by
[/kvalitet](https://ai-korpa.vercel.app/kvalitet), with `as_of: 2026-11-21` and completed
ingests between 17:43 and 17:49 UTC. The public API location remains
[the deployed service](https://korpa-api.onrender.com/api/quality), as documented in
[deploy.md](deploy.md); the static response identifies the page's actual published snapshot.

Sources below were resolved through the verified portal discovery interface, then downloaded
without conditional validators at 19:35:34–19:35:45 UTC (20:35:34–20:35:45 Europe/Belgrade).
All eight fresh responses were HTTP 200 and decoded successfully as UTF-8 (optional BOM
removed); all use semicolons. Exact first physical lines below preserve CSV quoting but omit
line terminators and any BOM. SHA-256 is over downloaded, HTTP-decoded bytes before UTF-8
decoding, so it includes any BOM. The existing `compat-2026-11.2` reader was used without
changes or database writes. Header failures count physical data lines as the reader does;
they do not prove that each row was semantically inspected. These are data observations,
not findings of legal non-compliance. Every proposal below awaits a maintainer decision;
no compatibility mappings or source repairs are implemented here.

### BRICO S DOO (`brico-s-doo`)

[Portal dataset](https://data.gov.rs/api/1/datasets/6a329a1969e6025495f2d2b6/) · [Downloaded CSV](https://data.gov.rs/s/resources/brico-s-doo-cenovnik/20261121-032950/cene-proizvoda-bricos-20261121.csv)

Fresh observation: `2026-11-21T19:35:34.175949+00:00`; 4,227,662 bytes; SHA-256
`5ae3b1d35d221e25bdb6257665f94a412d0891c6b45ac7d470b7eb7f137e27d9`.

Exact header:

```text
KATEGORIJA;NAZIV KATEGORIJE;Naziv proizvoda;Robna marka;Barkod proizvoda;Jedinica mere;Naziv trgovca - formata*;Datum cenovnika;Redovna cena;Cena po jedinici mere;Snižena cena;Datum početka sniženja;Datum kraja sniženja;Stopa PDV
```

The header has 14 columns: `VRSTA_CENOVNIKA` is missing and column 7 is
`Naziv trgovca - formata*` (literal trailing asterisk). All 32,713 records are rejected
at the header stage. The first data record additionally contains category `10000`, date
`21.11.2026`, and an empty required unit price; fixing the header alone would not establish
row validity.

Proposal: ask the publisher for the complete 15-column export with canonical format header,
explicit list type, category codes 1–25, `DD-MM-YYYY` dates and populated unit prices.
The maintainer should decide whether this non-grocery assortment belongs in discovery;
do not infer list type or recode its categories.

### Konovo doo (`konovo-doo`)

[Portal dataset](https://data.gov.rs/api/1/datasets/6a693202d31a9dd3073aaf73/) · [Downloaded CSV](https://konovo.rs/wp-content/uploads/cenovnik/cene_proizvoda_konovo.csv)

Fresh observation: `2026-11-21T19:35:35.174296+00:00`; 1,586,197 bytes; SHA-256
`06f07888c4e875be9d5da8ecb18ab28ffb208178fe92c389f602bbc86ce7408f`.

Exact header:

```text
Kategorija;"Naziv kategorije";"Naziv proizvoda";"Robna marka";"Barkod proizvoda";"Jedinica mere";"Naziv trgovca - formata";"Datum cenovnika";"Redovna cena";"Cena po jedinici mere";"Snižena cena";"Datum početka sniženja";"Datum kraja sniženja";"Stopa PDV";"Šifra proizvoda"
```

The file has 15 columns, but `Kategorija` and `Naziv kategorije` differ in case
from the required uppercase headers; the last column is `Šifra proizvoda` instead of
`VRSTA_CENOVNIKA`. All 10,061 records fail the header. The first final-column value is
`G-43816`, a product identifier, so treating it as a spelling alias would change meaning.

Proposal: request a separate contract export with canonical category headers, explicit list
type and no additional product-code column. Ask the maintainer to review assortment/category
scope (the first category name is `Tableti i Oprema za Tablete`); never substitute list types
for product identifiers.

### Leon Conditors DOO (`leon-conditors-doo`)

[Portal dataset](https://data.gov.rs/api/1/datasets/68f1db0682d3fdfbdceeabcb/) · [Downloaded CSV](https://www.leon.co.rs/cenovnik/cene-proizvoda-leon.csv)

Fresh observation: `2026-11-21T19:35:35.893326+00:00`; 1,560,523 bytes; SHA-256
`186e7d218a4ee3680d55359d1edeebc2c3f86c71a96966327b0c3db51a494fed`.

Exact header:

```text
KATEGORIJA;NAZIV KATEGORIJE;Naziv proizvoda;Robna marka;Barkod proizvoda;Jedinica mere;Naziv trgovca - formata;Datum cenovnika;Redovna cena;Cena po jedinici mere;Snižena cena;Datum početka sniženja;Datum kraja sniženja;Stopa PDV;VRSTA_CENOVNIKA
```

The deployed failure is a connection timeout, not a rejected CSV or HTTP error.
The [deployment job](https://github.com/spasojewagner/korpa/actions/runs/44931550566/job/136929067446)
records at `2026-11-21T17:46:27.1784846Z`:

```text
ERROR:root:Download failed for leon-conditors-doo: ConnectTimeout
```

The accompanying report has `http_status: 0`, zero rows and `download: 1`; the ingestion
client has a 60-second timeout. This identifies the observed exception, but does not prove
whether the underlying cause was routing, hosting or another connection problem.
The fresh download below succeeds with HTTP 200, decodes as UTF-8 and has the canonical
header. Parsing without writes yields 827 valid records of 9,670; independent rules count
8,843 discount failures and 4 unit failures. `Snižena cena` is literal `0` on 8,837 rows
(e.g. CSV line 2), and the four unit failures use `1kg/l`. These later row findings did
not cause the earlier download failure and are not a claim that a new import has run.

Proposal: retry the normal ingest from the deployment environment and check connectivity
if the timeout recurs; a maintainer can consider bounded transient-download retries separately.
Ask the publisher to leave absent discounts empty and publish valid unit values; do not
interpret zero as an absent discount or guess what `1kg/l` means.

### Planeta Sport (`planeta-sport`)

[Portal dataset](https://data.gov.rs/api/1/datasets/6acca84dc60236a1e2681a41/) · [Downloaded CSV](https://portal.planeta.services/api/media/price-reporting/cene_proizvoda_planetasport.csv)

Fresh observation: `2026-11-21T19:35:36.464269+00:00`; 487,719 bytes; SHA-256
`b1d4f5c6e0c7db87d60d6bf9e4208bc150eacf30b0b01fbe8e9f468701f9ecb4`.

Exact header:

```text
KATEGORIJA;NAZIV KATEGORIJE;Naziv proizvoda;Robna marka;Barkod proizvoda;Jedinica mere;Naziv trgovca;Datum cenovnika;Redovna cena;Cena po jedinici mere;Snižena cena;Datum početka sniženja;Datum kraja sniženja;Stopa PDV;VRSTA_CENOVNIKA
```

All 2,444 records fail because column 7 is `Naziv trgovca`, not
`Naziv trgovca - formata`. This is a UTF-8 header mismatch, not an encoding error. The first
published format value is `Planeta Sport - eplaneta.rs`.

Proposal: request the canonical format header from the publisher. Alternatively, the
maintainer can decide whether that exact header is a justified future one-to-one alias
after confirming that values identify formats; any approval needs a new counted profile.

### Qvattro Company (`qvattro-company`)

[Portal dataset](https://data.gov.rs/api/1/datasets/68f8cbfd1d835c729727825d/) · [Downloaded CSV](https://prodavnicasunce.rs/cenovnik/cene_proizvoda_QVATTRO_COMPANY.csv)

Fresh observation: `2026-11-21T19:35:36.941032+00:00`; 4,999,434 bytes; SHA-256
`58d583ef86cbaa02ae001c3c1a0e5c9443218c4a047837dc4958dec4b05ab33e`.

Exact header:

```text
KATEGORIJA;NAZIV KATEGORIJE;Naziv proizvoda;Robna marka;Barkod proizvoda;Jedinica mere;Naziv trgovca - format;Datum cenovnika;Redovna cena;Cena po jedinici mere;Snižena cena;Datum početka sniženja;Datum kraja sniženja;Stopa PDV;VRSTA_CENOVNIKA
```

All 29,791 records fail because column 7 is `Naziv trgovca - format`
(singular `format`), not `Naziv trgovca - formata`. The other 14 parsed header cells match.

Proposal: request the canonical header; alternatively submit this exact one-to-one spelling
variant for a maintainer decision in a future counted profile. No general suffix correction
or fuzzy header matching is justified.

### RIČ doo Prokuplje (`ric-doo-prokuplje`)

[Portal dataset](https://data.gov.rs/api/1/datasets/6a95ed3adf0d645f96b6f3de/) · [Downloaded CSV](https://www.podaci.ric.rs/cenovnici/cene_proizvoda_ric.csv)

Fresh observation: `2026-11-21T19:35:38.554612+00:00`; 4,190,562 bytes; SHA-256
`60947f91b5b8c42a20ef9db8146954e630b956757343ce99e3a9271ce65d44db`.

Exact header:

```text
KATEGORIJA;NAZIV KATEGORIJE;Naziv proizvoda;Robna marka;Barkod proizvoda;Jedinica mere;Naziv trgovca - formata;Datum cenovnika;Redovna cena;Cena po jedinici mere;Snižena cena;Datum početka sniženja;Datum kraja sniženja;Stopa PDV;VRSTA_CENOVNIKA
```

The canonical header is accepted and all 31,885 records are fully processed,
but none is valid. Every `Stopa PDV` is decimal text: `20.00` on 29,012 rows and `10.00`
on 2,873 rows; the contract requires integer text. Independently, 31,851 required
`Cena po jedinici mere` cells are empty. There are also 51 unapproved unit values:
`kgr` (16), `kon` (15), `kg.` (5), `km` (4), `kgm` (3), `set` (3), `om` (2),
`1` (2), `kob` (1). First-failure counts (`vat: 31834`, `unit: 51`) hide overlapping
price failures; independent counts are `vat: 31885`, `price: 31851`, `unit: 51`.
CSV line 2 has `Stopa PDV=20.00` and an empty unit price.

Proposal: request integer VAT, actual populated unit prices and explicit valid units from
the publisher. The maintainer may separately evaluate the two exact decimal VAT spellings,
but that alone would leave almost all rows invalid; do not calculate missing unit prices
or infer units from these abbreviations.

### Statovac (`statovac`)

[Portal dataset](https://data.gov.rs/api/1/datasets/6a0aecd5c320c889bd9a2a96/) · [Downloaded CSV](https://data.gov.rs/s/resources/cenovnici-statovac/20261107-033026/cene-proizvoda-kengur.csv)

Fresh observation: `2026-11-21T19:35:43.424111+00:00`; 5,315,775 bytes; SHA-256
`c72a690bca92d9c20907e0daa7e945815cb7f319fe66dc7af245982c97bba704`.

Exact header:

```text
КАТЕГОРИЈА;НАЗИВ КАТЕГОРИЈЕ;Назив производа;Робна марка;Баркод производа;Јединица мере;Назив трговца – формата;Датум ценовника;Редовна цена;Цена по јединици мере;Снижена цена;Датум почетка снижења;Датум краја снижења;Стопа ПДВ;ВРСТА_ЦЕНОВНИКА
```

All 22,300 records fail at the header: all 15 column names are Cyrillic,
including `КАТЕГОРИЈА` and `ВРСТА_ЦЕНОВНИКА`; column 7 also uses an en dash. UTF-8 decoding
succeeds, so this is not an encoding failure. Published values also include Cyrillic
units (`кг`: 15,824; `л`: 5,904; `ком`: 572) and list type `МЕСЕЧНИ_ПРЕСЕК` in line 2.
Header acceptance alone would not validate those values.

Proposal: request the canonical Latin contract export, or ask the maintainer to review a
complete, explicitly enumerated header/unit/list-type profile with deviation counters.
Do not transliterate arbitrary source data or silently turn Cyrillic values into valid ones.

### VP DIMA (`vp-dima`)

[Portal dataset](https://data.gov.rs/api/1/datasets/6a95aa4568bb7d8ad44b1e7d/) · [Downloaded CSV](https://vpdima.rs/cenovnik/cene_proizvoda_vpdima.csv)

Fresh observation: `2026-11-21T19:35:44.899283+00:00`; 4,596,747 bytes; SHA-256
`44506019ba8d51cd1ad6a14f8c21832aabd32513893e0649f54e1102537169af`.

Exact header:

```text
KATEGORIJA;NAZIV KATEGORIJE;Naziv proizvoda;Robna marka;Barkod proizvoda;Jedinica mere;Naziv trgovca - formata;Datum cenovnika;Redovna cena;Cena po jedinici mere;Snizena cena;Datum pocetka snizenja;Datum kraja snizenja;Stopa PDV;VRSTA_CENOVNIKA
```

Columns 11–13 are ASCII `Snizena cena`, `Datum pocetka snizenja` and
`Datum kraja snizenja`, instead of `Snižena cena`, `Datum početka sniženja` and
`Datum kraja sniženja`. UTF-8 decoding succeeds; the missing accents are present in the
published header itself. The fresh file has 25,465 rejected records, compared with 25,466
in the deployed report; its Last-Modified is `Sat, 21 Nov 2026 19:08:24 GMT`, after that
report's ingest. The header failure remains reproducible despite the changed row count.

Proposal: ask the publisher to restore these three canonical header spellings, or seek a
maintainer decision on exactly these three one-to-one aliases in a new counted profile.
Do not apply general accent-insensitive header matching.
