# Korpa design system

Civic, calm and fast. The data is the hero: prices, dates and sources, readable on a cheap phone in a shop aisle.
Not a government look: no coats of arms, flags, state colors or official-style seals.

## Principles
1. **Numbers first.** Prices are the largest text in their row, tabular numerals, aligned right.
2. **Every number has a date.** "Cenovnik od 19.11.2026." next to (or directly under) every price or total.
3. **Color is never the only signal.** "Najjeftinije", "Sniženo", "Poskupelo" are always icon + text.
4. **Honest comparisons.** A partial basket is never ranked next to a complete one without saying so.
5. **Light pages.** Home under 100 KB JS (gzip); no chart library on Home; charts are small hand-written SVG.

## Color (tokens in `theme.css`)
| Token | Hex | Use | Contrast on `paper` |
|---|---|---|---|
| `ink` | #13233A | body text, headings | 14.9:1 |
| `ink-soft` | #34465E | secondary text | 9.1:1 |
| `ink-muted` | #5B6A7D | meta text, input borders | 5.2:1 (4.7:1 on `paper-raised`) |
| `brand` | #1F4D3A | buttons, links, focus ring | 9.1:1; white on brand 9.6:1 |
| `brand-subtle` | #E2EFE6 | "Najjeftinije" badge bg | `brand` text on it 8.1:1 |
| `discount` / `-subtle` | #9A3B1E / #F8E7DE | "Sniženo" badge | 5.8:1 |
| `warn` / `-subtle` | #7A4E00 / #FBF0D8 | stale data, partial basket | 6.4:1 |
| `danger` / `-subtle` | #A12A2A / #F9E3E3 | errors, price increase | 6.0:1 |
| `paper`, `paper-raised`, `line` | #FBF8F2, #F3ECDF, #DCCDB1 | page, cards, dividers | `line` is decorative only |

## Type
- Source Sans 3 (variable, self-hosted via `@fontsource-variable/source-sans-3`, subsets `latin-ext` + `cyrillic`).
  Set `<html lang="sr-Latn">` / `lang="sr-Cyrl"` so Serbian Cyrillic forms (italic б, г, д, п, т) are used; check it
  renders correctly, otherwise switch to Noto Sans.
- Base 18 px (`text-base`), body line height 1.6, max line length ~70ch. Scale: sm 15, lg 20, xl 24, 2xl 32, 3xl 40.
- Prices: `tabular-nums font-semibold`. Old (regular) price when discounted: `line-through text-ink-muted` with
  visually hidden "redovna cena".

## Numbers, dates, copy
- Money comes from the API in para (integer). Format once, in `formatPrice(para)`, with
  `Intl.NumberFormat('sr-Latn-RS', { style: 'currency', currency: 'RSD' })` → "129,99 RSD". Never format in components.
- Dates: `DD.MM.YYYY.` ("19.11.2026."), Europe/Belgrade.
- Unit price: "259,98 RSD/kg" next to the price on product and comparison views.
- All UI copy lives in `src/i18n/sr-Latn.ts` (keys, no copy inside components). Cyrillic is produced by
  transliteration at runtime. UI copy and category names are transliterated; **product names and brands are shown
  exactly as the retailer published them** (they are data, e.g. "Coca-Cola" must stay as is).

## Components (`apps/web/src/components`, typed, tested, axe-checked)
| Component | Notes |
|---|---|
| `Price` | para → formatted, optional discounted + regular, unit price |
| `SourceDate` | "Cenovnik od …"; warns (icon + text) if older than 3 days |
| `Badge` | variants `cheapest`, `discount`, `partial`, `increase`, `decrease`; icon + text always |
| `SearchForm` | `role="search"`, label visible, submits to `/pretraga?q=`; no autocomplete in v1 |
| `ProductCard` | name, brand, unit, min–max price, number of formats, add to basket |
| `PriceComparison` | two-column table (caption, row headers), cheapest first (`aria-sort`), ties share the badge, unit price under each price |
| `QuantityStepper` | − / number input / +, labelled per product, 1–99 |
| `BasketSummary` | per retailer/format total, complete vs partial (badge + count of missing items) |
| `ScriptToggle` | "Latinica / Ћирилица" radio group, persisted, sets `lang` on `<html>` |
| `Sparkline` | SVG, 12–24 points, `role="img"` + text summary ("Najniža … najviša …") |
| `StateView` | loading skeleton (no layout shift), empty, error with retry, offline |
| `SiteFooter` | sources, data license, disclaimer from `AGENTS.md` |

## Layout
Mobile first, one column up to 640 px, content max width 72rem. Header: logo wordmark (text, no emblem), search,
basket link with item count (`aria-live="polite"` on change), script toggle. Touch targets ≥ 44 × 44 px.
