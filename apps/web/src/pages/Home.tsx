import { Link, createLazyRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { SearchForm } from '../components'
import { useI18n } from '../i18n/I18nProvider'
import { fetchCategories, fetchQuality, type Schemas } from '../lib/api'
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

function useCategories(): Schemas['CategoryItem'][] {
  const [categories, setCategories] = useState<Schemas['CategoryItem'][]>([])
  useEffect(() => {
    let live = true
    fetchCategories()
      .then((items) => { if (live) setCategories(items.filter((item) => item.n_products > 0)) })
      .catch(() => undefined)
    return () => {
      live = false
    }
  }, [])
  return categories
}

function Home() {
  const { t, tp } = useI18n()
  const navigate = useNavigate()
  const newest = useNewestListDate()
  const categories = useCategories()
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
      {categories.length > 0 && (
        <section aria-labelledby="categories" className="mt-10">
          <h2 id="categories" className="text-xl font-semibold">{t('categoriesHeading')}</h2>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {categories.map((category) => (
              <li key={category.code}>
                <Link to="/pretraga" search={{ kategorija: category.code }}
                  className="flex min-h-11 items-center justify-between gap-3 rounded-md border border-line bg-white px-4 py-2 text-ink hover:bg-paper-raised">
                  <span>{category.name}</span>
                  <span className="text-sm text-ink-muted tabular-nums">{tp('basketItems', category.n_products)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
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
