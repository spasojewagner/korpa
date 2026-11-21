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

## Five live downloads and local ingest reports

The full exact dataset and resource URLs, response validators, download sizes, error counts,
and conditional response statuses are retained in [portal-observations.json](portal-observations.json).
All five downloads were parsed locally and produced one `ingest_runs` row each in PostgreSQL.
No raw CSV was put in the database or committed.

| Publisher slug | Parsed data records | Accepted | First validation errors |
| --- | ---: | ---: | --- |
| `beltorg-doo-1` | 2,075 | 0 | `list_type` |
| `lidl` | 12,628 | 0 | `header` |
| `luki-komerc-d-o-o` | 25,181 | 0 | `list_type`, `unit` |
| `metro-cash-carry-doo-beograd` | 38,039 | 0 | `unit` |
| `yuhor-d-o-o` | 4,612 | 0 | `list_type` |

Errors are grouped by the first failing rule per row, so `unit` can mask an additional invalid
list type. Header mismatch rejects the file. A schema-compliant fixture exercises successful
current-price and monthly-snapshot writes in PostgreSQL tests; fixture success is not real-data
acceptance. The roadmap's requirement for usable data from at least five retailers is **not met**.

Four resource servers returned Last-Modified; Luki, Metro, and Yuhor also returned ETag.
Conditional requests actually returned **304** for all four. Lidl returned neither validator.
Do not assume support across hosts. The client prefers If-None-Match, otherwise
If-Modified-Since, and handles 304 without reparsing or rewriting prices. Validators are persisted
only for clean imports; a source URL change invalidates stored validators.

The five datasets declare `license: sodl`. The portal license registry is available at:
https://data.gov.rs/api/1/datasets/licenses/
The exact license text and attribution wording must be reviewed before public redistribution.
The app already links the portal and displays the required independence disclaimer; it does not
claim a single license applies to every resource. The adapter reports each dataset's license.

## Contract question requiring a maintainer decision

Published files commonly use `MESECNI_PRESEK` and `VAZECI_CENOVNIK`, whereas AGENTS.md requires
`MESEČNI_PRESEK` and `VAŽEĆI_CENOVNIK`. Uppercase units such as `KG` also occur. Some column
headers differ. These values are rejected and counted, not transliterated, lowercased, or repaired.
Should explicitly documented source variants be accepted through a versioned compatibility
adapter, or should the contract stay strict until publishers change their files? This decision
is left open in the ingest PR; no compatibility mapping has been introduced.

## Persistence decisions and remaining limits

- Canonical product/category descriptions are first seen; retailer-specific names are upserted
  separately. Products are matched only by their exact 13-character barcode.
- Imports are atomic per publisher and serialized with a transaction advisory lock. Older
  lists cannot revert newer current prices. Conflicting duplicates within one date are rejected.
- Identical duplicate rows count as valid source records but collapse to one write.
- Daily history stores the last changed price for a format/barcode/source date. Repeating an
  identical price does not append history. Monthly observations remain immutable.
- Current prices are upserted; absence from a later file does not yet delete a product. A policy
  for complete-file replacement and withdrawn listings is still needed before comparison pages.
- Daily history older than 120 days is removed. Monthly observations are retained. Size is logged
  before and after each ingest, warns at 70%, and rejects/rolls back writes at 90% of 1 GB.
- The 700k-row/100–200 MB estimate is unverified because real rows fail the supplied contract.
  The implementation uses indexed per-row upserts; benchmark and batch optimization are still
  needed before nightly operation at the largest forecast scale.
- Raw-download artifact retention, scheduled ingestion, static JSON exports, API product reads,
  and deployment belong to later phases. No retailer HTML is scraped.
