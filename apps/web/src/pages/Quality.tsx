import { useQuery } from '@tanstack/react-query'
import { createLazyRoute } from '@tanstack/react-router'
import { StateView } from '../components'
import { useI18n } from '../i18n/I18nProvider'
import { codeLabels, type CopyKey } from '../i18n/sr-Latn'
import { ApiError, fetchQuality, type Schemas } from '../lib/api'
import { formatDate, formatNumber, formatPercent } from '../lib/format'
import { usePageMeta } from '../lib/meta'
import { WithQuery } from '../lib/query'

const statusKey: Record<Schemas['QualityItem']['status'], CopyKey> = {
  ok: 'statusOk', partial: 'statusPartial', failed: 'statusFailed', never: 'statusNever',
}

function Counts({ label, counts }: { label: string; counts: Record<string, number> }) {
  const { tr } = useI18n()
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
  const { t, tp } = useI18n()
  usePageMeta(t('qualityHeading'))
  const query = useQuery({ queryKey: ['quality'], queryFn: fetchQuality })
  return (
    <>
      <h1 className="text-2xl font-semibold">{t('qualityHeading')}</h1>
      <p className="mt-4 max-w-3xl text-ink-soft">{t('qualityIntro')}</p>
      <p className="mt-2 max-w-3xl text-ink-soft">{t('qualityAdjusted')}</p>
      <p className="mt-2 max-w-3xl text-ink-soft">{t('qualitySuspected')}</p>
      <div className="mt-6 overflow-x-auto">
        {query.isPending ? (
          <StateView kind="loading" lines={2} />
        ) : query.isError ? (
          <StateView kind={query.error instanceof ApiError && query.error.status === 0 ? 'offline' : 'error'}
            onRetry={() => void query.refetch()} />
        ) : (
          <table className="w-full min-w-[40rem] border-collapse text-left">
            <caption className="sr-only">{t('qualityCaption')}</caption>
            <thead>
              <tr className="border-b border-ink-muted text-sm text-ink-soft">
                <th scope="col" className="py-2 pr-4 font-semibold">{t('colRetailer')}</th>
                <th scope="col" className="py-2 pr-4 font-semibold">{t('colStatus')}</th>
                <th scope="col" className="py-2 pr-4 font-semibold">{t('colRows')}</th>
                <th scope="col" className="py-2 pr-4 font-semibold">{t('colList')}</th>
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
                    <td className="py-3 pr-4 tabular-nums">
                      {valid != null && total ? t('rowsOf', {
                        valid: formatNumber(valid), total: formatNumber(total), pct: formatPercent(valid / total),
                      }) : '—'}
                    </td>
                    <td className="py-3 pr-4">
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
    </>
  )
}

export const Route = createLazyRoute('/kvalitet')({ component: () => <WithQuery><QualityPage /></WithQuery> })
