# Deploy

Free tier only: Neon (Postgres), Render (API), Vercel (static site), GitHub Actions (nightly job).

```
GitHub Actions (.github/workflows/deploy.yml)
  nightly 03:17 UTC, manual, and on every push to main
  → alembic upgrade head            (Neon)
  → korpa ingest --all              (nightly and manual only)
  → export_static → public/data/*.json
  → vercel build + deploy --prod    (site with that morning's data)

Render: korpa-api (infra/render.yaml), auto-deploys main; sleeps after 15 min idle.
Vercel: korpa-web, root directory apps/web, deployed only from the workflow (no Git integration).
```

The site reads `/data/categories.json` and `/data/quality.json` first, so Home and the data quality page never
wait for a sleeping API. Search, product and basket call the API; the first request after idle takes about a minute.

## Settings (names only; values are entered in the dashboards, never committed)

| Where | Name | Value |
|---|---|---|
| GitHub → Settings → Secrets → Actions | `DATABASE_URL` | Neon connection string (pooled) |
| | `VERCEL_TOKEN` | Vercel access token for this project |
| | `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | from the Vercel project settings |
| Render → korpa-api → Environment | `DATABASE_URL` | same Neon connection string |
| | `CORS_ORIGINS` | the production site URL, e.g. `https://korpa.vercel.app` |
| Vercel → korpa-web → Environment (Production) | `VITE_API_URL` | the Render API URL, e.g. `https://korpa-api.onrender.com` |

Plain `postgresql://…?sslmode=require&channel_binding=require` URLs work for both drivers: the sync driver gets
`postgresql+psycopg`, the async API translates `sslmode` to asyncpg's `ssl` and drops `channel_binding`.

## Operations
- **Run now:** GitHub → Actions → deploy → Run workflow.
- **Invalid rows** do not fail the job (`--report-row-errors`); they are counted on `/kvalitet`. A crash, a failed
  migration or the storage guard (90 % of Neon's 1 GB) fails it, and GitHub e-mails the repository owner.
- **Rollback the site:** Vercel → Deployments → previous deployment → Promote to Production.
- **Rollback the API:** Render → korpa-api → Events → previous deploy → Rollback. Migrations are additive.
