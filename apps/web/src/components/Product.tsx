import type { ReactNode } from 'react'
import { usePageI18n } from '../i18n/usePageI18n'
import { formatDate, formatMonth, formatPrice } from '../lib/format'
import { Badge } from './Badge'
import { Icon } from './Icon'
import { Price, SourceDate } from './Price'

export interface ProductSummary {
  barcode: string
  name: string
  brand: string
  unit: string
  minPara: number
  maxPara: number
  nFormats: number
  anyDiscount: boolean
  listDate: string
}

export interface ProductCardProps {
  product: ProductSummary
  href: string
  /** Lets the router supply its own link element; defaults to a plain anchor. */
  renderLink?: (children: ReactNode, className: string) => ReactNode
  onAdd?: (barcode: string) => void
  /** Already in the basket: the add button becomes a static confirmation. */
  added?: boolean
  headingLevel?: 2 | 3
  today?: Date
}

export function ProductCard({ product, href, renderLink, onAdd, added = false, headingLevel = 2, today }: ProductCardProps) {
  const { t, tp } = usePageI18n()
  const { barcode, name, brand, unit, minPara, maxPara, nFormats, anyDiscount, listDate } = product
  const linkClass = 'text-ink underline-offset-4 hover:underline'
  const Heading = headingLevel === 3 ? 'h3' : 'h2'
  const price = minPara === maxPara
    ? formatPrice(minPara)
    : t('priceRange', { min: formatPrice(minPara), max: formatPrice(maxPara) })
  return (
    <article className="card-link flex h-full flex-col gap-4 rounded-lg border border-line bg-white p-5">
      <div>
        <Heading className="font-display text-2xl font-semibold">
          {renderLink ? renderLink(name, linkClass) : <a href={href} className={linkClass}>{name}</a>}
        </Heading>
        <p className="text-sm text-ink-muted">{[brand, unit].filter(Boolean).join(' · ')}</p>
      </div>
      <div className="flex flex-col gap-1">
        <span className="font-display text-2xl font-semibold tabular-nums">{t('priceFrom', { price: formatPrice(minPara) })}</span>
        {minPara !== maxPara && <span className="font-display text-lg tabular-nums">{price}</span>}
        <span className="text-sm text-ink-soft">{tp('formats', nFormats)}</span>
      </div>
      {anyDiscount && <span><Badge variant="discount" /></span>}
      <div className="mt-auto"><SourceDate date={listDate} today={today} /></div>
      {onAdd && (
        // One button in both states, so keyboard focus stays in place after adding.
        <button type="button" aria-disabled={added || undefined} onClick={() => { if (!added) onAdd(barcode) }}
          className="btn btn-secondary self-start">
          {added && <Icon name="check" />}
          {t(added ? 'inBasket' : 'addToBasket')}<span className="sr-only">: {name}</span>
        </button>
      )}
    </article>
  )
}

export interface FormatPrice {
  formatId: string | number
  retailer: string
  format: string
  /** Price the buyer pays now, in para. */
  para: number
  regularPara?: number | null
  unitPara?: number | null
  discountTo?: string | null
  listDate: string
}

/** Prices of one product across retail formats, cheapest first. Ties share the "Najjeftinije" badge. */
export function PriceComparison({ rows, unit, today }: { rows: FormatPrice[]; unit?: string; today?: Date }) {
  const { t } = usePageI18n()
  const sorted = [...rows].sort((a, b) => a.para - b.para || a.retailer.localeCompare(b.retailer, 'sr'))
  const cheapest = sorted[0]?.para
  return (
    <table className="w-full border-collapse text-left">
      <caption className="sr-only">{t('comparisonCaption')}</caption>
      <thead>
        <tr className="border-b border-line text-sm uppercase tracking-wide text-ink-muted">
          <th scope="col" className="py-2 pr-4 font-semibold">{t('colFormat')}</th>
          <th scope="col" aria-sort="ascending" className="py-2 text-right font-semibold">{t('colPrice')}</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((row) => {
          const discounted = row.regularPara != null && row.regularPara > row.para
          return (
            <tr key={row.formatId} className="border-b border-line align-top">
              <th scope="row" className="py-3 pr-4 text-left font-normal">
                <span className="block font-semibold">{row.retailer}</span>
                <span className="block text-sm text-ink-soft">{row.format}</span>
                <span className="my-1 flex flex-wrap gap-2">
                  {row.para === cheapest && <Badge variant="cheapest" />}
                  {discounted && (
                    <Badge variant="discount">
                      {row.discountTo ? t('badgeDiscountUntil', { date: formatDate(row.discountTo) }) : undefined}
                    </Badge>
                  )}
                </span>
                <SourceDate date={row.listDate} today={today} />
              </th>
              <td className="py-3 text-right tabular-nums">
                <Price para={row.para} regularPara={row.regularPara} unitPara={row.unitPara} unit={unit} />
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export interface MonthPoint {
  /** First day of the month, ISO ('2026-03-01'). */
  month: string
  para: number
}

/** Small price history line. The SVG is decorative; the caption carries the facts. */
export function Sparkline({ points, width = 240, height = 56 }: { points: MonthPoint[]; width?: number; height?: number }) {
  const { t } = usePageI18n()
  if (points.length < 2) return null
  const values = points.map((point) => point.para)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const x = (index: number) => 2 + (index / (points.length - 1)) * (width - 4)
  const y = (value: number) => height - 2 - ((value - min) / range) * (height - 4)
  const path = points.map((point, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)},${y(point.para).toFixed(1)}`).join(' ')
  const low = points[values.indexOf(min)]
  const high = points[values.indexOf(max)]
  const last = points[points.length - 1]
  return (
    <figure className="m-0 flex flex-col gap-1">
      <svg aria-hidden="true" focusable="false" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none"
        className="h-32 w-full text-brand">
        <path d={path} fill="none" stroke="currentColor" strokeWidth={2} vectorEffect="non-scaling-stroke" />
        <circle cx={x(points.length - 1)} cy={y(last.para)} r={3} fill="currentColor" />
      </svg>
      <figcaption className="text-sm text-ink-muted">
        {t('sparklineSummary', {
          min: formatPrice(min), minMonth: formatMonth(low.month),
          max: formatPrice(max), maxMonth: formatMonth(high.month),
        })}
      </figcaption>
    </figure>
  )
}
