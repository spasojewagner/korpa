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
Project foundation is implemented. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and roadmap.

## Stack
FastAPI · REST + GraphQL (Strawberry) · PostgreSQL (Neon) · SQLAlchemy + Alembic · React 19 · TypeScript · Vite ·
TanStack Router/Query · Tailwind · Radix UI · GitHub Actions (CI + nightly ingest) · Playwright · pytest · Vitest

## Local setup

Requirements: Python 3.12, uv, Node.js 22.12+ (or a compatible newer LTS), Docker Compose v2,
and GNU Make. Run commands from the repository root.

```sh
uv sync --extra dev --frozen
npm ci
npm ci --prefix apps/web
cp .env.example .env
make dev
```

The empty example variables use local development defaults: Postgres at
`postgresql+psycopg://korpa:korpa@localhost:5432/korpa`, API at
`http://127.0.0.1:8000/health`, and web at `http://127.0.0.1:5173`.
These database credentials are for the local Compose service only. Set `DATABASE_URL` and a
comma-separated `CORS_ORIGINS` for other environments. The development page shows an honest
empty state and the required independence disclaimer; it offers a Latin/Cyrillic UI toggle.

On Windows PowerShell without Make, use `Copy-Item .env.example .env`, then:

```powershell
docker compose -f infra/docker-compose.yml up -d --wait
uv run --extra dev alembic -c apps/api/alembic.ini upgrade head
npm run dev
```

`npm run dev` runs API and web together. Ctrl+C stops both processes. Postgres stays running;
stop it with `docker compose -f infra/docker-compose.yml stop`.

## Checks

```sh
make lint
make test
make build
npm --prefix apps/web exec -- playwright install chromium
make e2e
```

Equivalent commands without Make:

```sh
uv run --extra dev ruff check .
uv run --extra dev mypy
uv run --extra dev pytest
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web test
npm --prefix apps/web run build
npm --prefix apps/web run e2e
```

CI installs locked dependencies and enforces Python lint/types/tests, migrations, frontend
lint/types/tests, production build, and the keyboard browser smoke test. Product API, GraphQL,
comparison pages, analytics, and deployment are later phases.
