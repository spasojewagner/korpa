import { ApiError, type Schemas } from './api'
import { MAX_ITEMS, MAX_QTY, type BasketItem } from './basket'
import { assistantCopy } from '../i18n/assistant'
import type { I18n } from '../i18n/I18nProvider'

export class AssistantError extends ApiError {
  constructor(status: number, readonly retryAfter: string | null = null) {
    super(status, 'assistant')
  }
}

const base = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request<T>(path: string, body?: Schemas['AiBasketRequest']): Promise<T> {
  const response = await fetch(base + path, body ? {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  } : undefined)
  if (!response.ok) throw new AssistantError(response.status, response.headers.get('Retry-After'))
  return await response.json() as T
}

export const assistantStatus = () => request<Schemas['AiStatus']>('/api/ai/status')
export const suggestBasket = (sentence: string) => request<Schemas['AiBasketResponse']>('/api/ai/basket', { sentence })

type AssistantKey = keyof typeof assistantCopy | 'errorMessage'
export function assistantText(i18n: Pick<I18n, 't' | 'tr'>) {
  return (key: AssistantKey, vars: Record<string, string | number> = {}): string => {
    if (key === 'errorMessage') return i18n.t(key)
    const translated = assistantCopy[key].split(/(\{\w+\})/)
      .map((part) => part.startsWith('{') ? part : i18n.tr(part)).join('')
    return translated.replace(/\{(\w+)\}/g, (match, name: string) =>
      name in vars ? String(vars[name]) : match)
  }
}

export function assistantErrorMessage(error: unknown, t: ReturnType<typeof assistantText>, now = Date.now()): string {
  if (error instanceof AssistantError) {
    if (error.status === 422) return t('assistantInvalid')
    if (error.status === 503) return t('assistantUnavailable')
    if (error.status === 429) {
      const header = error.retryAfter
      const seconds = header && /^\d+$/.test(header) ? Number(header) : header ? (Date.parse(header) - now) / 1000 : NaN
      return Number.isFinite(seconds)
        ? t('assistantWait', { minutes: Math.max(1, Math.ceil(seconds / 60)) })
        : t('assistantRateLimit')
    }
  }
  return t('errorMessage')
}

/** All or nothing when full; repeated selections and existing quantities are merged. */
export function mergeBasketItems(current: BasketItem[], chosen: BasketItem[]): BasketItem[] | null {
  const merged = new Map(current.map((item) => [item.barcode, { ...item }]))
  for (const item of chosen) {
    const qty = (merged.get(item.barcode)?.qty ?? 0) + item.qty
    merged.set(item.barcode, { barcode: item.barcode, qty: Math.min(MAX_QTY, Math.max(1, Math.round(qty))) })
  }
  return merged.size > MAX_ITEMS ? null : [...merged.values()]
}
