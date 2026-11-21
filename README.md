# Korpa

**Transparentnost cena namirnica u Srbiji, iz otvorenih podataka.**
Open-data price transparency for Serbian groceries.

Since September 2026, Serbian retailers must publish their price lists as machine-readable CSV files on the national
open data portal. Korpa turns those files into a tool people can actually use:

- search any product and compare its price across retail chains and store formats,
- build a basket and see which chain is cheapest for it,
- follow a monthly price index per product category,
- see which retailers publish complete, on-time data (a data-quality report),
- later: an AI basket assistant ("ručak za 4 osobe do 2.000 din") and an MCP server, always grounded in real prices.

> Nezavisan projekat zasnovan na otvorenim podacima. Nije povezan sa Ministarstvom.
> Independent project built on open data. Not affiliated with any government body.

## Status
Early development. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and roadmap.

## Stack
FastAPI · REST + GraphQL (Strawberry) · PostgreSQL (Neon) · SQLAlchemy + Alembic · React 19 · TypeScript · Vite ·
TanStack Router/Query · Tailwind · Radix UI · GitHub Actions (CI + nightly ingest) · Playwright · pytest · Vitest
