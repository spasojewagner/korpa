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

An explicitly requested live evaluation uses `--live` and requires `LLM_PROVIDER=gemini`, `groq` or `auto`,
`LLM_API_KEY`, and `LLM_MODEL`. Add `--record PATH` to save the actual raw responses, with the model
name, for later replay. Calls are sequential: Gemini pauses six seconds, Groq thirty seconds
between sentences by default. `--interval-seconds 6..60` overrides that interval. Temporary
HTTP 429/500/502/503/504, network and timeout failures retry the same sentence up to three
times, after 6, 12 and 24 seconds. A numeric `Retry-After` can extend a wait up to 300 seconds;
a longer quota-reset wait stops with a clear message instead of calling too early.
Each retry logs the sanitized provider status/message.
Permanent errors and exhausted retries stop the command with the error detail; recordings
already written are retained. Only successful responses are recorded, once per sentence.
Never commit a key.

## Groq on the free plan

Use `openai/gpt-oss-20b` with `LLM_PROVIDER=groq`, your Groq key in `LLM_API_KEY`, and
that model ID in `LLM_MODEL`. The existing async HTTP client is used without a new dependency.
Basket extraction and checked index notes use the same configured provider.

The request uses strict JSON Schema. Optional fields become nullable and objects are closed
on a copy of the schema; the application's validation and output contracts remain unchanged.
Truncated/refused responses fail explicitly. References:
[structured output](https://console.groq.com/docs/structured-outputs) and
[rate limits](https://console.groq.com/docs/rate-limits).

The documented free-plan limits for this model on 2026-11-24 are 30 requests/minute,
1,000/day, 8,000 tokens/minute and 200,000/day; the account's actual limits take precedence.
The conservative default spacing reduces request/token bursts. Other account traffic and
daily quotas can still prevent completion; no code can guarantee free-tier capacity.
Completed recordings survive failure. Recorded replay never calls a provider.

In GitHub Actions choose **AI evaluation → Run workflow**. Add the
repository secret `GROQ_API_KEY` from your free Groq account first; never paste it into a
report, commit or chat. In single-provider `groq` mode, leave the model input blank to use
`openai/gpt-oss-20b`. Missing credentials fail before any API request; the Gemini key is never
sent to Groq. Single-provider `gemini` uses the existing `LLM_API_KEY` and `LLM_MODEL` secrets.
`DATABASE_URL` is shared for read-only retrieval.
The workflow remains manual and has a sixty-minute timeout for throttled runs. It does not
enable billing or change production's provider configuration.

## Automatic Gemini–Groq failover

The workflow defaults to `provider: auto`. It starts with the Gemini credentials in
`LLM_API_KEY`/`LLM_MODEL` and uses the separate `GROQ_API_KEY` plus `GROQ_MODEL`
(default `openai/gpt-oss-20b`) for Groq. Both keys must be configured. In local/API
configuration set `LLM_PROVIDER=auto` and the same variables to opt into this behavior.
The workflow's optional `model` overrides Gemini in auto mode; `groq_model` selects its backup.

A quota/rate error, temporary outage, timeout, or rejected JSON generation switches the
same request to the alternate provider. Each provider keeps its own next-allowed-call time:
Gemini at least six seconds, Groq thirty, and longer server-supplied quota cooldowns.
There are at least six seconds between any two attempts. Daily-exhausted providers stay
idle while the other is used. The pool can return to a provider after its cooldown.
Authentication, bad request schemas and model refusals fail explicitly.

Provider switching is sequential and bounded to four attempts and at most five minutes of
waiting per request. If both quotas are exhausted, it stops clearly and retains completed
recordings. It does not manufacture missing answers or enable a paid plan.

Each JSONL response records its actual `provider` and `model`. The report lists all models
and providers used and labels mixed-provider scores explicitly. Recorded replay preserves
that attribution. Older recordings without a provider field still replay normally.

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
