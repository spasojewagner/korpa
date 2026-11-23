import { usePageI18n } from '../i18n/usePageI18n'
import { daysSince, formatDate, formatPrice } from '../lib/format'
import { Icon } from './Icon'

export interface PriceProps {
  /** Price the buyer pays now, in para. */
  para: number
  /** Regular price in para; shown struck through when higher than `para`. */
  regularPara?: number | null
  unitPara?: number | null
  unit?: string | null
  size?: 'md' | 'lg'
}

export function Price({ para, regularPara, unitPara, unit, size = 'md' }: PriceProps) {
  const { t } = usePageI18n()
  const discounted = regularPara != null && regularPara > para
  return (
    <span className="inline-flex flex-col">
      <span className="block">
        {discounted && (
          <del className="block text-sm text-ink-muted tabular-nums sm:mr-2 sm:inline-block">
            <span className="sr-only">{t('regularPrice')}: </span>
            {formatPrice(regularPara)}
          </del>
        )}
        <strong className={`font-semibold tabular-nums ${size === 'lg' ? 'text-2xl' : 'text-lg'}`}>
          {formatPrice(para)}
        </strong>
      </span>
      {unitPara != null && unit && (
        <span className="text-sm text-ink-muted tabular-nums">
          {t('perUnit', { price: formatPrice(unitPara), unit })}
        </span>
      )}
    </span>
  )
}

export interface SourceDateProps {
  /** ISO date of the price list ('YYYY-MM-DD'). */
  date: string
  staleAfterDays?: number
  /** Injected in tests; defaults to now. */
  today?: Date
}

/** "Cenovnik od 19.11.2026." with a visible warning when the list is older than `staleAfterDays`. */
export function SourceDate({ date, staleAfterDays = 3, today }: SourceDateProps) {
  const { t } = usePageI18n()
  const stale = daysSince(date, today) > staleAfterDays
  return (
    <span className="text-sm text-ink-muted">
      <time dateTime={date.slice(0, 10)}>{t('sourceDate', { date: formatDate(date) })}</time>
      {stale && (
        <span className="ml-2 inline-flex items-center gap-1 font-semibold text-warn">
          <Icon name="alert" />
          {t('staleData', { days: staleAfterDays })}
        </span>
      )}
    </span>
  )
}
