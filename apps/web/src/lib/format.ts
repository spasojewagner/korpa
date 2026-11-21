// All money arrives from the API as integer para (price × 100). Format it here, never in components.

// Browsers' locale data list RSD with 0 decimals and would round 139,99 to 140: always show para.
const money = new Intl.NumberFormat('sr-Latn-RS', {
  style: 'currency', currency: 'RSD', minimumFractionDigits: 2, maximumFractionDigits: 2,
})

export function formatPrice(para: number): string {
  return money.format(para / 100)
}

const count = new Intl.NumberFormat('sr-Latn-RS')
const percent = new Intl.NumberFormat('sr-Latn-RS', { style: 'percent', maximumFractionDigits: 0 })

export const formatNumber = (value: number): string => count.format(value)

const indexValue = new Intl.NumberFormat('sr-Latn-RS', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const times = new Intl.NumberFormat('sr-Latn-RS', { minimumFractionDigits: 1, maximumFractionDigits: 2 })

/** Index value with one decimal: 101.4 → '101,4'. */
export const formatIndex = (value: number): string => indexValue.format(value)
/** Relative change from a ratio: 1.014 → '+1,4 %'. */
// Built by hand: ICU versions differ on the space before % in Serbian; we always use a no-break space.
export function formatChange(ratio: number): string {
  const percent = Math.round((ratio - 1) * 1000) / 10
  const sign = percent > 0 ? '+' : percent < 0 ? '−' : ''
  return `${sign}${indexValue.format(Math.abs(percent))}\u00a0%`
}
/** A multiple: 1.6 → '1,6×'. */
export const formatTimes = (ratio: number): string => `${times.format(ratio)}×`
export const formatPercent = (ratio: number): string => percent.format(ratio)

/** ISO calendar date 'YYYY-MM-DD' → '19.11.2026.' Parsed as a plain date, so no time zone shift. */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split('-')
  return `${day}.${month}.${year}.`
}

/** '2026-03-01' → '03.2026.' for monthly series. */
export function formatMonth(iso: string): string {
  const [year, month] = iso.slice(0, 10).split('-')
  return `${month}.${year}.`
}

/** Whole days from an ISO date to `today` (local calendar). */
export function daysSince(iso: string, today: Date = new Date()): number {
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number)
  const then = Date.UTC(year, month - 1, day)
  const now = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((now - then) / 86_400_000)
}
