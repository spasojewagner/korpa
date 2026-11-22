import { useId } from 'react'
import { usePageI18n } from '../i18n/usePageI18n'
import type { Schemas } from '../lib/api'
import { formatPrice } from '../lib/format'
import { SourceDate } from './Price'

export function BasketSplit({ split, names, quantities }: {
  split: Schemas['BasketSplit']
  names: ReadonlyMap<string, { name: string }>
  quantities: ReadonlyMap<string, number>
}) {
  const { t, tp } = usePageI18n()
  const headingId = useId()
  const oldestDate = split.items.map((item) => item.list_date).sort()[0]
  return (
    <section aria-labelledby={headingId} className="mt-8 rounded-lg border border-line bg-white p-5">
      <h3 id={headingId} className="font-display text-2xl">{t('basketSplitHeading')}</h3>
      <p className="mt-2 text-ink-soft">{t('basketSplitNote')}</p>
      <p className="mt-4 font-display text-2xl font-semibold tabular-nums">{formatPrice(split.total_para)}</p>
      <p>{tp('basketStores', split.n_formats)}</p>
      <p className="mt-2">{split.saving_vs_best_para === null
        ? t('basketSplitNoComparison')
        : t('basketSplitSaving', { saving: formatPrice(split.saving_vs_best_para) })}</p>
      {oldestDate && <SourceDate date={oldestDate} />}
      <details className="mt-4">
        <summary className="min-h-11 cursor-pointer py-2 font-semibold text-brand">{t('basketSplitDetails')}</summary>
        <ul className="mt-2 divide-y divide-line">
          {split.items.map((item) => (
            <li key={item.barcode} className="flex min-w-0 flex-col gap-1 py-3">
              <span className="font-semibold">{names.get(item.barcode)?.name ?? item.barcode}</span>
              <span>{item.format.name}</span>
              <span className="tabular-nums">{t('basketSplitUnitPrice', {
                qty: quantities.get(item.barcode) ?? 1, price: formatPrice(item.price_para),
              })}</span>
              <SourceDate date={item.list_date} />
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}
