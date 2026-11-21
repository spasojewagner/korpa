import type { ReactNode } from 'react'
import { useI18n } from '../i18n/I18nProvider'
import { formatDate, formatMonth, formatPrice } from '../lib/format'
import { Badge } from './Badge'
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
  headingLevel?: 2 | 3
  today?: Date
}

export function ProductCard({ product, href, renderLink, onAdd, headingLevel = 2, today }: ProductCardProps) {
  const { t, tp } = useI18n()
  const { barcode, name, brand, unit, minPara, maxPara, nFormats, anyDiscount, listDate } = product
  const linkClass = 'text-ink underline-offset-4 hover:underline'
  const Heading = headingLevel === 3 ? 'h3' : 'h2'
  const price = minPara === maxPara
    ? formatPrice(minPara)
    : t('priceRange', { min: formatPrice(minPara), max: formatPrice(maxPara) })
  return (
    <article className="flex flex-col gap-3 rounded-lg border border-line bg-white p-4">
      <div>
        <Heading className="text-lg font-semibold">
          {renderLink ? renderLink(name, linkClass) : <a href={href} className={linkClass}>{name}</a>}
        </Heading>
        <p className="text-sm text-ink-muted">{[brand, unit].filter(Boolean).join(' · ')}</p>
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-lg font-semibold tabular-nums">{price}</span>
        <span className="text-sm text-ink-soft">{tp('formats', nFormats)}</span>
      </div>
      {anyDiscount && <span><Badge variant="discount" /></span>}
      <SourceDate date={listDate} today={today} />
      {onAdd && (
        <button type="button" onClick={() => onAdd(barcode)}
          className="min-h-11 self-start rounded-md border border-brand px-4 font-semibold text-brand hover:bg-brand-subtle">
          {t('addToBasket')}<span className="sr-only">: {name}</span>
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
  const { t } = useI18n()
  const sorted = [...rows].sort((a, b) => a.para - b.para || a.retailer.localeCompare(b.retailer, 'sr'))
  const cheapest = sorted[0]?.para
  return (
    <table className="w-full border-collapse text-left">
      <caption className="sr-only">{t('comparisonCaption')}</caption>
      <thead>
        <tr className="border-b border-ink-muted text-sm text-ink-soft">
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
              <td className="py-3 text-right">
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
  const { t } = useI18n()
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
        className="h-14 w-full max-w-60 text-brand">
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
