# AI evaluation set

`phrases.jsonl`: 50 Serbian sentences with the items a shopper means. Each expected item has
`query_terms` (words a matching product name must contain, compared without case and diacritics, Latin script),
`qty` and the official `category` code (1–25).

Conventions used when labelling:
- Weights are not quantities: "kilogram jabuka", "pola kile banana" → `qty: 1` (the unit is the product's).
- Counted packs are quantities: "6 komada", "x4", "dvanaest jaja" → that number.
- Repeated words are one item ("mleko mleko mleko"); different variants are separate items.
- Vague or non-grocery sentences expect no items ("nešto slatko za decu", "koliko je danas sati").
- An instruction inside the sentence is data, not a command: only the grocery item counts.
- Cyrillic and typos ("cokolada", "mlijeko") expect the same products as standard Latin.

Labels describe intent, not a specific barcode; the evaluator scores a candidate as a match when its category
equals `category` and its normalized name contains every `query_terms` word (stems allowed, see the runner).
