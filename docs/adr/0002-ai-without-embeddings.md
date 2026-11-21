# ADR 0002: AI basket without embeddings (v1)

**Status:** accepted, 2026-11-22

## Context
The plan mentioned pgvector for matching free-text grocery phrases to products. With live data there are about
92,000 products. A 384-dimension vector per product is about 140 MB, plus an HNSW index of similar size: roughly a
quarter of Neon's 1 GB, on top of growing price history. Query-time embeddings would also need a model in the API
(Render free: 512 MB RAM) or a second paid-quota API call per request.

## Decision
The language model only rewrites a sentence into short search queries and quantities (structured JSON, validated).
Matching uses the existing full-text + trigram search with its ranking. No embeddings, no pgvector in v1.

## Consequences
- No extra storage or memory; one model call per request; every price and product comes from the database.
- Synonyms the search does not know ("nešto za doručak") depend on the model choosing concrete product words.
- Accuracy is measured on 50 labelled phrases (`docs/ai-eval`). If top-5 match stays below 80 %, revisit
  embeddings for product names only, sized against the storage budget.
