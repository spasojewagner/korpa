# Deploy

Free tier only: Neon (Postgres), Render (API), Vercel (static site), GitHub Actions (nightly job).

- Site: https://ai-korpa.vercel.app
- API: https://korpa-api.onrender.com (`/health`, `/api/...`, `/graphql`)

```
GitHub Actions (.github/workflows/deploy.yml)
  nightly 03:17 UTC, manual, and on every push to main
  → alembic upgrade head            (Neon)
  → korpa ingest --all --archive-dir data/raw (nightly and manual only)
  → export_static → public/data/*.json
  → vercel build + deploy --prod    (site with that morning's data)

Render: korpa-api (infra/render.yaml), auto-deploys main; sleeps after 15 min idle.
Vercel: korpa, root directory apps/web, deployed only from the workflow (no Git integration).
```

The site reads `/data/categories.json`, `/data/quality.json`, `/data/index.json` and
`/data/signals.json` first, so Home, the data quality page and price index never wait for a sleeping API. The ingest refreshes completed-month
indices after history compaction; the export also refreshes them before reading. Current-month snapshots
are final. The export and `GET /api/index` append an on-read provisional point dated `as_of`.
`signals.json` matches `GET /api/signals?limit=200`; the endpoint defaults to 100 and accepts
an optional `type=jump|outlier|discount_after_jump` filter. Signals are prompts for review, never accusations.
The discount signal and informational name variants are documented in [signals.md](signals.md).
Search, product and basket call the API; the first request after idle takes about a minute.

## Settings (names only; values are entered in the dashboards, never committed)

| Where | Name | Value |
|---|---|---|
| GitHub → Settings → Secrets → Actions | `DATABASE_URL` | Neon connection string (pooled) |
| | `VERCEL_TOKEN` | Vercel access token for this project |
| | `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | from the Vercel project settings |
| Render → korpa-api → Environment | `DATABASE_URL` | same Neon connection string |
| | `CORS_ORIGINS` | `https://ai-korpa.vercel.app` plus the project's other `*.vercel.app` aliases |
| Vercel → korpa → Environment (Production) | `VITE_API_URL` | `https://korpa-api.onrender.com` |

Plain `postgresql://…?sslmode=require&channel_binding=require` URLs work for both drivers: the sync driver gets
`postgresql+psycopg`, the async API translates `sslmode` to asyncpg's `ssl` and drops `channel_binding`.

## Operations
- **Run now:** GitHub → Actions → deploy → Run workflow.
- **Invalid rows** do not fail the job (`--report-row-errors`); they are counted on `/kvalitet`. A crash, a failed
  migration or the storage guard (90 % of Neon's 1 GB) fails it, and GitHub e-mails the repository owner.
- **Rollback the site:** Vercel → Deployments → previous deployment → Promote to Production.
- **Rollback the API:** Render → korpa-api → Events → previous deploy → Rollback. Migrations are additive.

## CI security and measurements

The ingest writes downloaded HTTP 200 bodies byte-for-byte to `data/raw/` only when
`--archive-dir data/raw` is passed. Filenames are digests of source identity, not publisher
paths. Invalid CSVs are archived too; HTTP 304 has no new body. The deploy job uploads
these ignored local files as `raw-price-lists` for 7 days, including after ingest failure.
Raw files never enter the database or repository.

CI exports the frozen Python environment (including development tools) for `pip-audit`,
which fails on any known vulnerability. Both npm lockfiles are audited with a high/critical
failure threshold. The production CSP and other web security headers are read directly
from `apps/web/vercel.json` by Vite preview. E2e builds use the production API origin,
intercept it with fixtures, and fail on CSP console errors or violation events.

`npm --prefix apps/web run lighthouse` measures the production build on five routes with
mobile Lighthouse defaults and the same typed fixtures as e2e. Build with
`VITE_API_URL=https://korpa-api.onrender.com` first. The runner mocks API and static JSON
requests, seeds a populated basket, writes full HTML/JSON reports and `scores.md` to
`apps/web/lighthouse-results/`, and publishes the table in the CI job summary. Thresholds:
performance ≥ 90, accessibility = 100, best practices ≥ 95, SEO ≥ 95. Page improvements
identified by these measurements are a separate follow-up.

The API adds `nosniff` and `strict-origin-when-cross-origin`. `/mcp` and its children
share a limit of 60 requests/minute per socket client address, with problem+json 429 and
`Retry-After`. Like the AI limiter, it is in memory on a single API instance and resets
on restart; additional workers would each have their own limit. It does not trust raw
forwarded headers; the hosting proxy must supply the correct client address to ASGI.

## Manual live evaluation

The **AI evaluation** workflow accepts only a manual dispatch. It uses the existing
`LLM_API_KEY`, `LLM_MODEL` and `DATABASE_URL` secrets, sets `LLM_PROVIDER=gemini`, and
runs extraction plus read-only database retrieval. `live.jsonl` and `results-live.md`
are uploaded as `live-evaluation`; partial recordings are retained on failure. It does
not commit results. Only the maintainer should dispatch this workflow after reviewing
model quota and database access. Adding any new secret or paid service needs approval.
