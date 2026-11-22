import { useId } from 'react'
import { usePageI18n } from '../i18n/usePageI18n'
import { formatPrice } from '../lib/format'
import { Badge } from './Badge'
import { SourceDate } from './Price'

export interface BasketTotal {
  key: string
  retailer: string
  format: string
  totalPara: number
  complete: boolean
  /** Number of basket items this format does not sell. */
  missing: number
  /** Oldest price list date used in this total. */
  listDate: string
}

export interface BasketSummaryProps {
  totals: BasketTotal[]
  headingLevel?: 2 | 3
  today?: Date
}

/**
 * Complete baskets are ranked by total. Partial baskets are listed separately and never
 * share a ranking with complete ones: their totals are not comparable.
 */
export function BasketSummary({ totals, headingLevel = 2, today }: BasketSummaryProps) {
  const { t } = usePageI18n()
  const completeId = useId()
  const partialId = useId()
  const Heading = headingLevel === 3 ? 'h3' : 'h2'
  const complete = totals.filter((total) => total.complete).sort((a, b) => a.totalPara - b.totalPara)
  const partial = totals
    .filter((total) => !total.complete)
    .sort((a, b) => a.missing - b.missing || a.totalPara - b.totalPara)
  return (
    <div className="flex flex-col gap-8">
      {complete.length > 0 && (
        <section aria-labelledby={completeId}>
          <Heading id={completeId} className="mb-3 font-display text-2xl">{t('basketComplete')}</Heading>
          <TotalsList totals={complete} cheapest={complete[0].totalPara} today={today} />
        </section>
      )}
      {partial.length > 0 && (
        <section aria-labelledby={partialId}>
          <Heading id={partialId} className="mb-1 font-display text-2xl">{t('basketPartial')}</Heading>
          <p className="mb-3 text-ink-soft">{t('basketPartialNote')}</p>
          <TotalsList totals={partial} today={today} />
        </section>
      )}
    </div>
  )
}

function TotalsList({ totals, cheapest, today }: { totals: BasketTotal[]; cheapest?: number; today?: Date }) {
  const { t, tp } = usePageI18n()
  return (
    <ol className="flex flex-col gap-3">
      {totals.map((total, index) => (
        <li key={total.key} className={`grid items-start gap-4 rounded-lg border border-line p-5 ${
          total.complete ? 'grid-cols-[auto_minmax(0,1fr)] sm:grid-cols-[auto_minmax(0,1fr)_auto]' : 'sm:grid-cols-[minmax(0,1fr)_auto]'} ${
          total.totalPara === cheapest ? 'bg-brand-subtle' : total.complete ? 'bg-white' : 'bg-paper-raised'}`}>
          {total.complete && <span aria-hidden="true" className="font-display text-2xl font-semibold text-brand tabular-nums">{index + 1}.</span>}
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="font-semibold">{total.retailer}</span>
            <span className="text-sm text-ink-soft">{total.format}</span>
            <span className="flex flex-wrap gap-2">
              {total.totalPara === cheapest && <Badge variant="cheapest" />}
              {!total.complete && <Badge variant="partial">{tp('missing', total.missing)}</Badge>}
            </span>
            <SourceDate date={total.listDate} today={today} />
          </div>
          <span className={`${total.complete ? 'col-start-2 sm:col-start-auto' : ''} sm:text-right`}>
            <span className="sr-only">{t('colTotal')}: </span>
            <strong className={`font-display font-semibold tabular-nums ${total.complete ? 'text-2xl' : 'text-lg text-ink-soft'}`}>{formatPrice(total.totalPara)}</strong>
          </span>
        </li>
      ))}
    </ol>
  )
}
