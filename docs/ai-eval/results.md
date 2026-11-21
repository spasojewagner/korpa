# Basket extraction evaluation

**Smoke test only:** recorded responses may be hand-written fixtures; this replay is not evidence of live model quality.

- Model: hand-written fixture (no model call)
- Date: 2026-11-21 (Europe/Belgrade)
- Mode: recorded; retrieval: disabled
- Sentences: 50; invalid outputs: 0

N/A means a zero denominator. Retrieval counts unmatched expected items as misses.

| Metric | Overall | No items expected |
|---|---:|---:|
| Item recall | 89.9% | N/A |
| Item precision | 91.0% | 0.0% |
| Quantity accuracy (matched pairs) | 93.0% | N/A |
| Exact item count (sentences) | 94.0% | 50.0% |

## Ten worst sentences

Ranked by missed + extra items + incorrect matched quantities + invalid output; then retrieval misses when enabled. Ties use id order.

| Id | Sentence | Expected (query × qty; category) | Extracted (query × qty) | Errors |
|---|---|---|---|---:|
| 45 | hleb integralni i hleb beli | hleb integralni × 1; category 5; hleb beli × 1; category 5 | hleb × 1 | 3 |
| 18 | mleko 2,8% imlek | mleko imlek × 1; category 1 | mleko × 1 | 2 |
| 21 | mlijeko i jaja | mleko × 1; category 1; jaja × 1; category 1 | mlijeko × 1; jaja × 1 | 2 |
| 36 | prašak za pecivo i vanilin šećer | prašak pecivo × 1; category 13; vanilin × 1; category 13 | prašak za pecivo × 1; šećer × 1 | 2 |
| 47 | kesice za zamrzivač i aluminijumska folija | kese × 1; category 20; folija × 1; category 20 | kesice za zamrzivač × 1; aluminijumska folija × 1 | 2 |
| 48 | granule za psa 10 kg | pas × 1; category 25 | granule za pse × 1 | 2 |
| 5 | pet kesica čaja od nane | čaj nana × 5; category 2 | čaj nana × 1 | 1 |
| 12 | toalet papir 3 pakovanja | toalet papir × 3; category 20 | toalet papir × 1 | 1 |
| 15 | sir, šunka i kifle za doručak | sir × 1; category 1; šunka × 1; category 8; kifla × 1; category 5 | sir × 1; šunka × 1 | 1 |
| 19 | coca cola 2l | coca cola × 1; category 2 | coca cola × 2 | 1 |
