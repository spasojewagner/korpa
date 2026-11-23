import { pageCopy } from '../i18n/pages'
import { useQuery } from '@tanstack/react-query'
import { createLazyRoute } from '@tanstack/react-router'
import { StateView } from '../components'
import { usePageI18n } from '../i18n/usePageI18n'
import type { PageKey as CopyKey } from '../i18n/usePageI18n'
import { codeLabels } from '../i18n/quality-labels'
import { ApiError, fetchQuality, type Schemas } from '../lib/api'
import { formatDate, formatNumber, formatPercent } from '../lib/format'
import { usePageMeta } from '../lib/meta'
import { WithQuery } from '../lib/query'

const statusKey: Record<Schemas['QualityItem']['status'], CopyKey> = {
  ok: 'statusOk', partial: 'statusPartial', failed: 'statusFailed', never: 'statusNever',
}

function Counts({ label, counts }: { label: string; counts: Record<string, number> }) {
  const { tr } = usePageI18n()
  const entries = Object.entries(counts).filter(([, n]) => n > 0).sort(([, a], [, b]) => b - a)
  if (entries.length === 0) return null
  return (
    <div>
      <span className="font-semibold">{label}:</span>{' '}
      {entries.map(([code, n]) => `${tr(codeLabels[code] ?? code)} ${formatNumber(n)}`).join(', ')}
    </div>
  )
}

function QualityPage() {
  const { t, tp, tr } = usePageI18n()
  usePageMeta(t('qualityHeading'), tr(pageCopy.qualityDescription))
  const query = useQuery({ queryKey: ['quality'], queryFn: fetchQuality })
  return (
    <>
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">{t('qualityHeading')}</h1>
      <p className="mt-4 max-w-3xl text-lg text-ink-soft">{t('qualityIntro')}</p>
      <p className="mt-2 max-w-3xl text-ink-soft">{t('qualityAdjusted')}</p>
      <p className="mt-2 max-w-3xl text-ink-soft">{t('qualitySuspected')}</p>
      <div role="region" aria-label={t('qualityCaption')} tabIndex={0} className="mt-6 overflow-x-auto rounded-lg border border-line bg-white p-5">
        {query.isPending ? (
          <StateView kind="loading" lines={2} />
        ) : query.isError ? (
          <StateView kind={query.error instanceof ApiError && query.error.status === 0 ? 'offline' : 'error'}
            onRetry={() => void query.refetch()} />
        ) : (
          <table className="w-full min-w-[40rem] border-collapse text-left">
            <caption className="sr-only">{t('qualityCaption')}</caption>
            <thead>
              <tr className="border-b border-line text-sm uppercase tracking-wide text-ink-muted">
                <th scope="col" className="py-2 pr-4 font-semibold">{t('colRetailer')}</th>
                <th scope="col" className="py-2 pr-4 font-semibold">{t('colStatus')}</th>
                <th scope="col" className="py-2 pr-4 text-right font-semibold">{t('colRows')}</th>
                <th scope="col" className="py-2 pr-4 text-right font-semibold">{t('colList')}</th>
                <th scope="col" className="py-2 font-semibold">{t('colNotes')}</th>
              </tr>
            </thead>
            <tbody>
              {query.data.retailers.map((retailer) => {
                const { rows_valid: valid, rows_total: total, days_since_list_date: days } = retailer
                return (
                  <tr key={retailer.slug} className="border-b border-line align-top">
                    <th scope="row" className="py-3 pr-4 font-semibold">{retailer.name}</th>
                    <td className="py-3 pr-4">{t(statusKey[retailer.status])}</td>
                    <td className="py-3 pr-4 text-right tabular-nums">
                      {valid != null && total ? t('rowsOf', {
                        valid: formatNumber(valid), total: formatNumber(total), pct: formatPercent(valid / total),
                      }) : '—'}
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums">
                      {retailer.list_date ? (
                        <>
                          <time dateTime={retailer.list_date}>{formatDate(retailer.list_date)}</time>
                          {days != null && <span className="block text-sm text-ink-muted">{days === 0 ? t('today') : tp('daysAgo', days)}</span>}
                        </>
                      ) : '—'}
                    </td>
                    <td className="py-3 text-sm text-ink-soft">
                      <Counts label={t('rejected')} counts={retailer.errors} />
                      <Counts label={t('adjusted')} counts={retailer.deviations} />
                      <Counts label={t('suspected')} counts={retailer.suspected_errors} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
      {query.data?.name_variants && (
        <section aria-labelledby="name-variants" className="mt-8 rounded-lg border border-line bg-paper-raised p-5">
          <h2 id="name-variants" className="font-display text-2xl">{t('nameVariantsHeading')}</h2>
          <p className="mt-2 text-ink-soft">{t('nameVariantsIntro')}</p>
          <p className="mt-2">{t('nameVariantsCount', {
            count: formatNumber(query.data.name_variants.barcodes),
            share: formatPercent(query.data.name_variants.share_of_products),
            date: formatDate(query.data.as_of),
          })}</p>
          <ul className="mt-4 space-y-3">
            {query.data.name_variants.examples.map((example) => (
              <li key={example.barcode} className="break-words">
                <span className="font-semibold">{example.barcode}</span>
                <ul>{example.names.map((name) => (
                  <li key={`${name.retailer}-${name.name}`}>{name.retailer}: {name.name}</li>
                ))}</ul>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}

export const Route = createLazyRoute('/podaci/kvalitet')({ component: () => <WithQuery><QualityPage /></WithQuery> })
