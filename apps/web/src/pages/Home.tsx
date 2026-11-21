import { Link, createLazyRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { SearchForm } from '../components'
import { useI18n } from '../i18n/I18nProvider'
import { fetchQuality } from '../lib/api'
import { formatDate } from '../lib/format'
import { usePageMeta } from '../lib/meta'

// Home avoids TanStack Query on purpose (bundle budget); one small fetch is enough here.
function useNewestListDate(): string | null {
  const [newest, setNewest] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    fetchQuality()
      .then((report) => {
        const dates = report.retailers.map((retailer) => retailer.list_date).filter((date): date is string => !!date)
        if (live) setNewest(dates.sort().at(-1) ?? null)
      })
      .catch(() => undefined)
    return () => {
      live = false
    }
  }, [])
  return newest
}

function Home() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const newest = useNewestListDate()
  usePageMeta()
  return (
    <>
      <p className="mb-3 font-semibold text-brand">{t('eyebrow')}</p>
      <h1 className="max-w-2xl text-3xl font-semibold">{t('title')}</h1>
      <p className="my-4 max-w-2xl text-lg text-ink-soft">{t('intro')}</p>
      {newest && <p className="text-sm text-ink-muted">{t('freshness', { date: formatDate(newest) })}</p>}
      <div className="mt-8 max-w-2xl">
        <SearchForm onSearch={(q) => navigate({ to: '/pretraga', search: { q } })} />
      </div>
      <section aria-labelledby="examples" className="mt-10">
        <h2 id="examples" className="text-xl font-semibold">{t('examplesHeading')}</h2>
        <ul className="mt-3 flex flex-wrap gap-2">
          {t('examples').split(', ').map((term) => (
            <li key={term}>
              <Link to="/pretraga" search={{ q: term }}
                className="inline-flex min-h-11 items-center rounded-md border border-ink-muted bg-white px-4 text-ink hover:bg-paper-raised">
                {term}
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <section aria-labelledby="how" className="mt-12 max-w-2xl rounded-lg bg-paper-raised p-6">
        <h2 id="how" className="text-xl font-semibold">{t('howHeading')}</h2>
        <ol className="mt-3 flex list-decimal flex-col gap-2 pl-5 text-ink-soft">
          <li>{t('how1')}</li>
          <li>{t('how2')}</li>
          <li>{t('how3')}</li>
        </ol>
      </section>
    </>
  )
}

export const Route = createLazyRoute('/')({ component: Home })
