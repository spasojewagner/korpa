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


## Running the evaluation

Run from the repository root after `uv sync --extra dev --frozen`:

```sh
uv run python -m korpa_api.ai.evaluate
uv run python -m korpa_api.ai.evaluate --recorded docs/ai-eval/recorded.jsonl --out docs/ai-eval/results.md
```

`recorded.jsonl` is a **hand-written fixture**, covering all 50 ids with intentionally imperfect
responses. It is not a model benchmark. The committed `results.md` is only a replay smoke test.
Each JSONL row contains `id` and raw model `text`; optional `model` metadata identifies the source.
Recorded mode needs neither network nor keys. Missing, duplicate or unexpected ids fail the command.
Invalid model output is scored as an empty extraction and counted in the report.

An explicitly requested live evaluation uses `--live` and requires `LLM_PROVIDER=gemini`,
`LLM_API_KEY`, and `LLM_MODEL`. Add `--record PATH` to save the actual raw responses, with the model
name, for later replay. Calls are sequential with at least six seconds between them. Temporary
HTTP 429/500/502/503/504, network and timeout failures retry the same sentence up to three
times, after 6, 12 and 24 seconds. Each retry logs the sanitized provider status/message.
Permanent errors and exhausted retries stop the command with the error detail; recordings
already written are retained. Only successful responses are recorded, once per sentence.
Never commit a key.

`--database` additionally requires `DATABASE_URL` and runs the normal repository search for every
extracted query in a read-only transaction. Top-1 and top-5 use all expected items as the denominator;
unmatched expected items are misses. Labels do not filter the search. The report contains no product
prices. `--phrases PATH` selects another labelled set for local tests without editing this one.

Item recall and precision are micro-averaged across items; quantity accuracy uses matched pairs.
Exact item count is averaged across sentences. Metrics are also shown separately for sentences with
no expected items. A zero denominator is reported as N/A. Worst sentences are ranked by missed items,
extra items and incorrect matched quantities (plus invalid outputs); retrieval misses break ties
when enabled, followed by id order. CI checks successful execution, with no minimum score threshold.

Goal sentences (a meal or an occasion instead of products) may return items with `proposed: true`.
They are suggestions the shopper confirms, so the evaluation drops them and scores only named products.
