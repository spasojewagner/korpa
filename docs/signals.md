# Signals and name variants

Signals invite review; they do not establish a violation. Existing `jump` and `outlier`
rules remain as specified in `tasks/M4b.md`.

## Sniženje posle skoka redovne cene

`discount_after_jump` checks a product within the same retail format:

- The current list is dated on or before `as_of`, its discounted price is set, and
  `disc_from <= as_of`, and `disc_to` is either absent (open-ended) or at least `as_of`.
  A missing start date does not establish an active discount.
- A consecutive pair of `price_changes` observations has a positive old regular price
  and a new regular price at least 120% and at most 300% of that old price.
- The rise date is in `[disc_from - 60 days, disc_from)`. The preceding observation may
  be older than this window. Future observations never enter the calculation.
- The active discounted price is at least 98% of the regular price before that rise.
  Thus a discount less than 2% below the old price can still produce a signal.

Integer prices are compared by cross multiplication before ratio rounding. Only the latest qualifying
rise per product and format produces a signal, using the existing order: rise date descending,
exact rise ratio descending, barcode, type, format id.
Rises above 3× are excluded from this signal; existing suspected-error counts are unchanged.

`GET /api/signals?type=discount_after_jump` filters the new type. Unfiltered results include
all three types. `signals.json` equals `GET /api/signals?limit=200` for the same `as_of`.
Limits remain 1–200, default 100. Existing items retain their original fields.

The new item contains the common barcode, canonical name, retailer and format, plus:

| Field | Meaning |
| --- | --- |
| `old_regular_para`, `reference_para` | Regular price before the rise, in para |
| `new_regular_para`, `price_para` | Regular price at the rise, in para |
| `discounted_para` | Currently discounted price, in para |
| `rise_date`, `date` | Date of the observed rise |
| `disc_from` | Discount start date |
| `as_of` | Date on which the discount is checked |
| `ratio` | New / old regular price, rounded to two decimals |

GraphQL and MCP do not expose signals, so their existing surfaces remain unchanged.
History retention (120 days) and incomplete retailer observations can limit detection;
absence of a signal does not establish that a discount is meaningful.

## Isti barkod, različiti nazivi

`GET /api/quality` and `quality.json` include `name_variants`:

- `barcodes`: number of barcodes with more than one distinct `product_names.raw_name`
  across retailers after lower-casing, removing punctuation, collapsing whitespace and
  trimming leading/trailing whitespace. Published names remain unchanged in examples.
- `share_of_products`: this count divided by all rows in `products`, a fraction from 0 to 1;
  zero when there are no products. Products without retailer names remain in the denominator.
- `examples`: up to five barcodes in ascending order, each with up to three distinct names
  ordered by raw name. Each name has its retailer; where several retailers use exactly the
  same name, the first retailer is the representative. Name and retailer ordering use
  PostgreSQL's `C` collation so capitalization and sample selection are stable across locales.

The quality page dates this informational block with the response's `as_of`. Name differences
do not modify retailer status, errors or deviations. They may reflect spelling, capitalization,
packaging descriptions or naming conventions and are not automatically treated as errors.
