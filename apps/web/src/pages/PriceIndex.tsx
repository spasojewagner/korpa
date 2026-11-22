import { pageCopy } from '../i18n/pages'
import { useQuery } from '@tanstack/react-query'
import { Link, createLazyRoute, useLoaderData } from '@tanstack/react-router'
import { useState } from 'react'
import { Badge, StateView } from '../components'
import { usePageI18n } from '../i18n/usePageI18n'
import { indexNotesCopy } from '../i18n/index-notes'
import type { PageKey as CopyKey } from '../i18n/usePageI18n'
import {
  fetchIndex, fetchSignals, latestPoint, type IndexCategory, type IndexPoint, type IndexResponse, type Signal,
  type SignalType,
} from '../lib/analytics'
import { ApiError } from '../lib/api'
import { formatChange, formatDate, formatIndex, formatMonth, formatNumber, formatPrice, formatTimes } from '../lib/format'
import { usePageMeta } from '../lib/meta'
import { WithQuery } from '../lib/query'

function Change({ point }: { point: IndexPoint }) {
  if (point.value === null || point.value === 100) return null
  const ratio = point.value / 100
  return <Badge variant={ratio > 1 ? 'increase' : 'decrease'}>{formatChange(ratio)}</Badge>
}

function PointNote({ point, dark = false }: { point: IndexPoint; dark?: boolean }) {
  const { t } = usePageI18n()
  return (
    <span className={`text-sm ${dark ? 'text-sand' : 'text-ink-muted'}`}>
      {point.provisional ? t('indexProvisional', { date: formatDate(point.month) }) : formatMonth(point.month)}
    </span>
  )
}

function Overall({ category }: { category: IndexCategory }) {
  const { t } = usePageI18n()
  const point = latestPoint(category)
  if (!point || point.value === null) return null
  return (
    <section aria-labelledby="overall" className="overflow-hidden rounded-lg bg-brand-deep text-paper">
      <div aria-hidden="true" className="kilim" />
      <div className="p-5 sm:p-8">
      <h2 id="overall" className="font-display text-2xl">{t('indexOverall')}</h2>
      <p className="mt-2 flex flex-wrap items-baseline gap-3">
        <strong className="font-display text-5xl font-semibold tabular-nums sm:text-6xl">{formatIndex(point.value)}</strong>
        <Change point={point} />
      </p>
      <p className="mt-4 flex flex-wrap gap-x-4"><PointNote point={point} dark />
        <span className="text-sm text-sand">{t('colProducts')}: {formatNumber(point.n_products)}</span>
      </p>
      </div>
    </section>
  )
}

function Notes({ notes, asOf }: { notes: IndexResponse['notes']; asOf: string }) {
  const { tr } = usePageI18n()
  if (!notes?.items.length) return null
  return (
    <section aria-labelledby="index-notes" className="max-w-3xl rounded-lg border border-line bg-white p-5">
      <h2 id="index-notes" className="font-display text-2xl">{tr(indexNotesCopy.heading)}</h2>
      <ul className="mt-2 list-disc pl-5">
        {notes.items.map((text) => <li key={text} className="mt-1">{tr(text)}</li>)}
      </ul>
      <p className="mt-3 text-sm text-ink-muted">
        {tr(indexNotesCopy.label).replace('{date}', formatDate(asOf))}
      </p>
    </section>
  )
}

function CategoryTable({ categories }: { categories: IndexCategory[] }) {
  const { t } = usePageI18n()
  return (
    <div role="region" aria-label={t('indexCaption')} tabIndex={0} className="overflow-x-auto rounded-lg border border-line bg-white p-5">
      <table className="w-full min-w-[32rem] border-collapse text-left">
        <caption className="sr-only">{t('indexCaption')}</caption>
        <thead>
          <tr className="border-b border-line text-sm uppercase tracking-wide text-ink-muted">
            <th scope="col" className="py-2 pr-4 font-semibold">{t('colCategory')}</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">{t('colIndex')}</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">{t('colChange')}</th>
            <th scope="col" className="py-2 text-right font-semibold">{t('colProducts')}</th>
          </tr>
        </thead>
        <tbody>
          {categories.map((category) => {
            const point = latestPoint(category)
            return (
              <tr key={category.code} className="border-b border-line align-top">
                <th scope="row" className="py-3 pr-4 font-normal">
                  <Link to="/pretraga" search={{ kategorija: category.code }} className="text-ink underline-offset-4 hover:underline">
                    {category.name}
                  </Link>
                  {point && <span className="mt-1 block"><PointNote point={point} /></span>}
                </th>
                <td className="py-3 pr-4 text-right tabular-nums">
                  {point?.value != null ? formatIndex(point.value) : <span className="text-sm text-ink-muted">{t('indexTooFew')}</span>}
                </td>
                <td className="py-3 pr-4 text-right tabular-nums">{point && <Change point={point} />}</td>
                <td className="py-3 text-right tabular-nums">{point ? formatNumber(point.n_products) : '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

const filters: { value: SignalType | 'all'; label: CopyKey }[] = [
  { value: 'all', label: 'signalsAll' },
  { value: 'jump', label: 'signalsJump' },
  { value: 'outlier', label: 'signalsOutlier' },
  { value: 'discount_after_jump', label: 'signalsDiscountAfterJump' },
]

function SignalItem({ signal }: { signal: Signal }) {
  const { t } = usePageI18n()
  const prices = { after: formatPrice(signal.price_para), before: formatPrice(signal.reference_para), reference: formatPrice(signal.reference_para) }
  return (
    <li className="card-link flex flex-col gap-2 rounded-lg border border-line bg-white p-5">
      <span className="flex flex-wrap items-center gap-2">
        <Link to="/proizvod/$barcode" params={{ barcode: signal.barcode }} className="font-semibold text-ink underline-offset-4 hover:underline">
          {signal.name}
        </Link>
        <Badge variant="increase">{t(signal.type === 'jump' ? 'signalsJump' : signal.type === 'outlier' ? 'signalsOutlier' : 'signalsDiscountAfterJump')}</Badge>
      </span>
      <span className="text-sm text-ink-soft">{signal.retailer} · {signal.format} · <time dateTime={signal.date}>{formatDate(signal.date)}</time></span>
      <span className="text-ink-soft">
        {signal.type === 'discount_after_jump'
          ? t('signalDiscountAfterJumpRule', {
              before: formatPrice(signal.old_regular_para), after: formatPrice(signal.new_regular_para),
              discounted: formatPrice(signal.discounted_para), start: formatDate(signal.disc_from),
              asOf: formatDate(signal.as_of),
            })
          : signal.type === 'jump'
            ? t('signalJumpRule', { ...prices, change: formatChange(signal.ratio) })
            : t('signalOutlierRule', { ...prices, ratio: formatTimes(signal.ratio) })}
      </span>
    </li>
  )
}

function Signals() {
  const { t } = usePageI18n()
  const [filter, setFilter] = useState<SignalType | 'all'>('all')
  const query = useQuery({ queryKey: ['signals'], queryFn: fetchSignals })
  const items = query.data?.items.filter((item) => filter === 'all' || item.type === filter) ?? []
  return (
    <section aria-labelledby="signals" className="mt-12">
      <h2 id="signals" className="font-display text-2xl">{t('signalsHeading')}</h2>
      <p className="mt-2 max-w-3xl text-lg text-ink-soft">{t('signalsIntro')}</p>
      <div role="group" aria-label={t('signalsFilter')} className="mt-4 flex flex-wrap gap-2">
        {filters.map(({ value, label }) => (
          <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}
            className="min-h-11 rounded-full border border-ink-muted bg-white px-4 font-semibold aria-pressed:border-brand aria-pressed:bg-brand aria-pressed:text-white">
            {t(label)}
          </button>
        ))}
      </div>
      <div className="mt-4">
        {query.isPending ? <StateView kind="loading" lines={2} />
          : query.isError && !(query.error instanceof ApiError && query.error.status === 404)
            ? <StateView kind="error" onRetry={() => void query.refetch()} />
            : items.length === 0 ? <StateView kind="empty" message={t('signalsEmpty')} />
              : <ul className="grid gap-4 sm:grid-cols-2">{items.map((item) => <SignalItem key={`${item.type}-${item.barcode}-${item.format}-${item.date}`} signal={item} />)}</ul>}
      </div>
    </section>
  )
}

function PriceIndexPage() {
  const { t, tr } = usePageI18n()
  usePageMeta(t('indexHeading'), tr(pageCopy.priceindexDescription))
  const initialData = useLoaderData({ from: '/podaci/indeks' }) ?? undefined
  const query = useQuery({ queryKey: ['index'], queryFn: fetchIndex, initialData })
  const overall = query.data?.categories.find((category) => category.code === 0)
  const categories = query.data?.categories.filter((category) => category.code !== 0) ?? []
  return (
    <>
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">{t('indexHeading')}</h1>
      {query.isPending ? (
        <div className="mt-6"><StateView kind="loading" lines={2} /></div>
      ) : query.isError ? (
        <div className="mt-6">
          {query.error instanceof ApiError && query.error.status === 404
            ? <StateView kind="empty" title={t('indexHeading')} message={t('indexSoon')} />
            : <StateView kind="error" onRetry={() => void query.refetch()} />}
        </div>
      ) : (
        <>
          <p className="mt-4 max-w-3xl text-lg text-ink-soft">{t('indexIntro', { month: formatMonth(query.data.base_month) })}</p>
          <details className="mt-3 max-w-3xl">
            <summary className="cursor-pointer font-semibold text-brand">{t('indexMethodHeading')}</summary>
            <p className="mt-2 text-ink-soft">{t('indexMethod')}</p>
          </details>
          <div className="mt-6 flex flex-col gap-8">
            {overall && <Overall category={overall} />}
            <Notes notes={query.data.notes} asOf={query.data.as_of} />
            <CategoryTable categories={categories} />
          </div>
        </>
      )}
      <Signals />
    </>
  )
}

export const Route = createLazyRoute('/podaci/indeks')({ component: () => <WithQuery><PriceIndexPage /></WithQuery> })
