import { Link, useNavigate } from '@tanstack/react-router'
import { Icon, SearchForm } from '../components'
import { sectionsCopy } from '../i18n/home-sections'
import { useI18n } from '../i18n/I18nProvider'
import { fetchIndex, latestPoint } from '../lib/analytics'
import { formatChange, formatDate, formatIndex, formatMonth } from '../lib/format'
import { useStatic, type HomeData } from './home-data'

function How() {
  const { tr } = useI18n()
  return (
    <section aria-labelledby="how" className="bg-paper-raised py-20">
      <div className="wrap">
        <h2 id="how" className="max-w-2xl font-display text-3xl font-semibold sm:text-4xl">{tr(sectionsCopy.howHeading)}</h2>
        <ol className="mt-10 grid gap-5 md:grid-cols-3">
          {sectionsCopy.how.map(([title, text], index) => (
            <li key={title} className="flex flex-col gap-3 rounded-lg bg-paper p-7">
              <span aria-hidden="true" className="font-display text-5xl font-semibold text-paprika tabular-nums">{index + 1}</span>
              <h3 className="text-xl font-semibold">{tr(title)}</h3>
              <p className="text-ink-soft">{tr(text)}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

function Browse({ data }: { data: HomeData | null }) {
  const { tr, tp } = useI18n()
  const navigate = useNavigate()
  const chip = 'inline-flex min-h-11 items-center rounded-full border border-ink-muted bg-white px-4 text-ink hover:border-ink hover:bg-paper-raised'
  return (
    <section id="pretraga" aria-labelledby="browse" className="wrap scroll-mt-6 py-20">
      <h2 id="browse" className="max-w-2xl font-display text-3xl font-semibold sm:text-4xl">{tr(sectionsCopy.searchHeading)}</h2>
      <div className="mt-8 max-w-2xl">
        <SearchForm onSearch={(q) => navigate({ to: '/pretraga', search: { q } })} />
      </div>
      <h3 className="mt-6 text-sm font-semibold uppercase tracking-wide text-ink-muted">{tr(sectionsCopy.examplesLabel)}</h3>
      <ul className="mt-3 flex flex-wrap gap-2">
        {sectionsCopy.examples.map((term) => (
          <li key={term}><Link to="/pretraga" search={{ q: term }} className={chip}>{tr(term)}</Link></li>
        ))}
      </ul>
      {data && data.categories.length > 0 && (
        <>
          <h3 className="mt-12 font-display text-2xl font-semibold">{tr(sectionsCopy.categoriesHeading)}</h3>
          <ul className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.categories.map((category) => (
              <li key={category.code}>
                <Link to="/pretraga" search={{ kategorija: category.code }}
                  className="card-link flex min-h-16 items-center gap-4 rounded-lg border border-line bg-white px-4 py-3 text-ink">
                  <span aria-hidden="true" className="grid size-11 shrink-0 place-items-center rounded-full bg-brand-subtle text-brand">
                    <svg className="size-5"><use href={`/icons/categories.svg#c${category.code}`} /></svg>
                  </span>
                  <span className="flex-1 leading-snug">{category.name}</span>
                  <span className="text-sm text-ink-muted tabular-nums">{tp('basketItems', category.n_products)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

function IndexBand() {
  const { tr } = useI18n()
  const index = useStatic(fetchIndex)
  const overall = index?.categories.find((category) => category.code === 0)
  const point = overall ? latestPoint(overall) : undefined
  return (
    <section aria-labelledby="index-band" className="bg-brand-deep text-paper">
      <div aria-hidden="true" className="kilim" />
      <div className="wrap grid items-center gap-10 py-20 lg:grid-cols-[1.2fr_1fr]">
        <div>
          <h2 id="index-band" className="font-display text-3xl font-semibold sm:text-4xl">{tr(sectionsCopy.indexHeading)}</h2>
          <p className="mt-4 max-w-xl text-lg text-sand">{tr(sectionsCopy.indexText)}</p>
          <Link to="/podaci" className="btn btn-on-dark mt-8">
            {tr(sectionsCopy.openData)}
            <Icon name="arrowRight" className="size-5" />
          </Link>
        </div>
        {index && point?.value != null && (
          <div className="rounded-xl border border-sand/40 p-8">
            <p className="font-display text-7xl font-semibold tabular-nums">{formatIndex(point.value)}</p>
            <p className="mt-2 text-xl font-semibold tabular-nums">{formatChange(point.value / 100)}</p>
            <p className="mt-4 text-sand">{tr(sectionsCopy.indexValue).replace('{month}', formatMonth(index.base_month))}</p>
            <p className="mt-1 text-sm text-sand">{tr(sectionsCopy.indexAsOf).replace('{date}', formatDate(index.as_of))}</p>
          </div>
        )}
      </div>
    </section>
  )
}

const trustIcons = ['check', 'shield', 'code'] as const

function Trust() {
  const { tr } = useI18n()
  return (
    <section aria-labelledby="trust" className="wrap py-20">
      <h2 id="trust" className="max-w-2xl font-display text-3xl font-semibold sm:text-4xl">{tr(sectionsCopy.trustHeading)}</h2>
      <ul className="mt-10 grid gap-8 md:grid-cols-3">
        {sectionsCopy.trust.map(([title, text], index) => (
          <li key={title} className="border-t-2 border-ink pt-5">
            <Icon name={trustIcons[index]} className="size-6 text-brand" />
            <h3 className="mt-3 text-xl font-semibold">{tr(title)}</h3>
            <p className="mt-2 text-ink-soft">{tr(text)}</p>
          </li>
        ))}
      </ul>
      <Link to="/podaci/kvalitet" className="mt-10 inline-flex min-h-11 items-center gap-2 font-semibold text-brand underline underline-offset-4">
        {tr(sectionsCopy.trustLink)}
        <Icon name="arrowRight" className="size-4" />
      </Link>
    </section>
  )
}

export default function HomeSections({ data }: { data: HomeData | null }) {
  return (
    <>
      <How />
      <Browse data={data} />
      <IndexBand />
      <Trust />
    </>
  )
}
