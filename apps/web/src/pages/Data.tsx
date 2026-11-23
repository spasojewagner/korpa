import { Link, createLazyRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Icon, type IconName } from '../components'
import { dataCopy } from '../i18n/data'
import { usePageI18n } from '../i18n/usePageI18n'
import { fetchQuality } from '../lib/api'
import { formatDate, formatNumber, formatPercent } from '../lib/format'
import { usePageMeta } from '../lib/meta'
import { WithQuery } from '../lib/query'

const API = 'https://korpa-api.onrender.com'
const SITE = 'https://ai-korpa.vercel.app'

function Stats() {
  const { tr } = usePageI18n()
  const query = useQuery({ queryKey: ['quality'], queryFn: fetchQuality })
  const retailers = query.data?.retailers.filter((retailer) => (retailer.rows_valid ?? 0) > 0) ?? []
  const valid = retailers.reduce((sum, retailer) => sum + (retailer.rows_valid ?? 0), 0)
  const total = query.data?.retailers.reduce((sum, retailer) => sum + (retailer.rows_total ?? 0), 0) ?? 0
  const stats = [
    [query.data ? formatNumber(retailers.length) : '–', dataCopy.statRetailers],
    [query.data ? formatNumber(valid) : '–', dataCopy.statRows],
    [total ? formatPercent(valid / total) : '–', dataCopy.statShare],
  ]
  return (
    <section aria-labelledby="stats" aria-busy={query.isPending} className="rounded-lg bg-paper-raised p-6 sm:p-8">
      <h2 id="stats" className="text-sm font-semibold uppercase tracking-wide text-ink-muted">{tr(dataCopy.statsLabel)}</h2>
      <dl className="mt-4 grid gap-6 sm:grid-cols-3">
        {stats.map(([value, label]) => (
          <div key={label} className="flex flex-col-reverse">
            <dt className="mt-1 text-ink-soft">{tr(label)}</dt>
            <dd className="font-display text-4xl font-semibold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 min-h-[1.5em] text-sm text-ink-muted">{query.data ? tr(dataCopy.statsSource).replace('{date}', formatDate(query.data.as_of)) : '\u00a0'}</p>
    </section>
  )
}

function Card({ to, icon, title, text }: { to: '/podaci/indeks' | '/podaci/kvalitet' | '/podaci/api' | '/o-projektu'; icon: IconName; title: string; text: string }) {
  const { tr } = usePageI18n()
  return (
    <li>
      <Link to={to} className="card-link flex h-full flex-col gap-3 rounded-lg border border-line bg-white p-6">
        <span aria-hidden="true" className="grid size-11 place-items-center rounded-full bg-brand-subtle text-brand">
          <Icon name={icon} className="size-5" />
        </span>
        <span className="font-display text-xl font-semibold text-ink">{title}</span>
        <span className="text-ink-soft">{tr(text)}</span>
        <span aria-hidden="true" className="mt-auto inline-flex items-center gap-1 font-semibold text-brand">
          <Icon name="arrowRight" className="size-4" />
        </span>
      </Link>
    </li>
  )
}

function Overview() {
  const { t, tr } = usePageI18n()
  usePageMeta(t('navData'), tr(dataCopy.overviewDescription))
  return (
    <div className="flex flex-col gap-10">
      <div className="max-w-3xl">
        <h1 className="font-display text-3xl font-semibold sm:text-4xl">{tr(dataCopy.overviewTitle)}</h1>
        <p className="mt-4 text-lg text-ink-soft">{tr(dataCopy.overviewLead)}</p>
      </div>
      <Stats />
      <ul className="grid gap-4 sm:grid-cols-2">
        <Card to="/podaci/indeks" icon="chart" title={t('dataIndex')} text={dataCopy.cardIndexText} />
        <Card to="/podaci/kvalitet" icon="shield" title={t('navQuality')} text={dataCopy.cardQualityText} />
        <Card to="/podaci/api" icon="code" title={t('dataApi')} text={dataCopy.cardApiText} />
        <Card to="/o-projektu" icon="search" title={tr(dataCopy.cardMethodTitle)} text={dataCopy.cardMethodText} />
      </ul>
    </div>
  )
}

const endpoints: [string, string][] = [
  ['GET /api/search?q=mleko', dataCopy.epSearch],
  ['GET /api/categories', dataCopy.epCategories],
  ['POST /api/basket', dataCopy.epBasket],
  ['GET /api/index', dataCopy.epIndex],
  ['GET /api/signals', dataCopy.epSignals],
  ['GET /api/quality', dataCopy.epQuality],
]

const mcpConfig = `{
  "mcpServers": {
    "korpa": { "type": "http", "url": "${API}/mcp/" }
  }
}`

function Code({ children }: { children: string }) {
  return (
    <pre lang="en" className="overflow-x-auto rounded-md bg-brand-deep p-4 text-sm text-paper"><code>{children}</code></pre>
  )
}

function ApiPage() {
  const { tr } = usePageI18n()
  usePageMeta(tr(dataCopy.apiTitle), tr(dataCopy.apiDescription))
  const link = 'font-semibold text-brand underline underline-offset-2'
  return (
    <article className="flex max-w-3xl flex-col gap-10">
      <div>
        <h1 className="font-display text-3xl font-semibold sm:text-4xl">{tr(dataCopy.apiTitle)}</h1>
        <p className="mt-4 text-lg text-ink-soft">{tr(dataCopy.apiLead)}</p>
        <p className="mt-4 rounded-md bg-warn-subtle p-4 text-ink">{tr(dataCopy.apiSleep)}</p>
      </div>
      <section aria-labelledby="rest">
        <h2 id="rest" className="font-display text-2xl font-semibold">{tr(dataCopy.restHeading)}</h2>
        <p className="mt-2"><code>{API}</code> · <a href={`${API}/docs`} className={link}>{tr(dataCopy.restDocs)}</a></p>
        <table className="mt-4 w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-ink-muted">
              <th scope="col" className="py-2 pr-4">{tr(dataCopy.colEndpoint)}</th>
              <th scope="col" className="py-2">{tr(dataCopy.colPurpose)}</th>
            </tr>
          </thead>
          <tbody>
            {endpoints.map(([endpoint, purpose]) => (
              <tr key={endpoint} className="border-b border-line align-top">
                <td className="py-3 pr-4"><code className="text-sm">{endpoint}</code></td>
                <td className="py-3 text-ink-soft">{tr(purpose)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section aria-labelledby="graphql">
        <h2 id="graphql" className="font-display text-2xl font-semibold">{tr(dataCopy.graphqlHeading)}</h2>
        <p className="mt-2 text-ink-soft">{tr(dataCopy.graphqlText)}</p>
        <p className="mt-2"><code>{API}/graphql</code></p>
      </section>
      <section aria-labelledby="mcp">
        <h2 id="mcp" className="font-display text-2xl font-semibold">{tr(dataCopy.mcpHeading)}</h2>
        <p className="mt-2 text-ink-soft">{tr(dataCopy.mcpText)}</p>
        <p className="mt-4">{tr(dataCopy.mcpConfig)}</p>
        <div className="mt-2"><Code>{mcpConfig}</Code></div>
      </section>
      <section aria-labelledby="files">
        <h2 id="files" className="font-display text-2xl font-semibold">{tr(dataCopy.filesHeading)}</h2>
        <p className="mt-2 text-ink-soft">{tr(dataCopy.filesText)}</p>
        <ul className="mt-3 flex flex-col gap-1">
          {['index.json', 'signals.json', 'quality.json', 'categories.json'].map((file) => (
            <li key={file}><a href={`${SITE}/data/${file}`} className={link}>{`/data/${file}`}</a></li>
          ))}
        </ul>
      </section>
    </article>
  )
}

export const OverviewRoute = createLazyRoute('/podaci')({ component: () => <WithQuery><Overview /></WithQuery> })
export const ApiRoute = createLazyRoute('/podaci/api')({ component: ApiPage })
