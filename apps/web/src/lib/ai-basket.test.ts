import { describe, expect, test } from 'vitest'
import { createI18n } from '../i18n/I18nProvider'
import { AssistantError, assistantErrorMessage, assistantText, mergeBasketItems, selectedTotal } from './ai-basket'
import { MAX_ITEMS } from './basket'

describe('merge proposed basket items', () => {
  test('merges existing and duplicate quantities without changing the inputs', () => {
    const current = [{ barcode: '8600000000001', qty: 2 }]
    expect(mergeBasketItems(current, [
      { barcode: '8600000000001', qty: 3 }, { barcode: '8600000000002', qty: 1 },
      { barcode: '8600000000002', qty: 4 },
    ])).toEqual([{ barcode: '8600000000001', qty: 5 }, { barcode: '8600000000002', qty: 5 }])
    expect(current[0].qty).toBe(2)
    expect(mergeBasketItems(current, [])).toEqual(current)
  })
  test('caps quantities and rejects overflow atomically, but permits merging into a full basket', () => {
    const current = Array.from({ length: MAX_ITEMS }, (_, i) => ({ barcode: String(i).padStart(13, '0'), qty: 90 }))
    expect(mergeBasketItems(current, [{ barcode: current[0].barcode, qty: 20 }])?.[0].qty).toBe(99)
    expect(mergeBasketItems(current, [{ barcode: '9999999999999', qty: 1 }])).toBeNull()
    expect(current[0].qty).toBe(90)
  })
})

describe('assistant error messages', () => {
  const t = assistantText(createI18n('latn'))
  test('maps validation, unavailability, and network errors to local copy', () => {
    expect(assistantErrorMessage(new AssistantError(422), t)).toBe(t('assistantInvalid'))
    expect(assistantErrorMessage(new AssistantError(503), t)).toBe('Pomoćnik trenutno nije dostupan')
    expect(assistantErrorMessage(new TypeError('fetch'), t)).toBe(t('errorMessage'))
  })
  test('rounds Retry-After seconds and HTTP dates up to minutes', () => {
    const now = Date.parse('2026-11-21T12:00:00Z')
    expect(assistantErrorMessage(new AssistantError(429, '121'), t)).toContain('3 min.')
    expect(assistantErrorMessage(new AssistantError(429, 'Sat, 21 Nov 2026 12:01:01 GMT'), t, now)).toContain('2 min.')
    expect(assistantErrorMessage(new AssistantError(429, '0'), t)).toContain('1 min.')
    for (const value of [null, 'invalid']) expect(assistantErrorMessage(new AssistantError(429, value), t)).toBe(t('assistantRateLimit'))
  })
  test('error copy follows the selected script', () => {
    expect(assistantErrorMessage(new AssistantError(503), assistantText(createI18n('cyrl')))).toBe('Помоћник тренутно није доступан')
    expect(assistantErrorMessage(new AssistantError(429, '121'), assistantText(createI18n('cyrl')))).toContain('3 мин.')
    expect(assistantText(createI18n('cyrl'))('assistantCounter', { count: 12 })).toBe('12/300 знакова')
  })
})

describe('lowest total of the chosen products', () => {
  test('counts quantity times the cheapest price of the chosen candidate; skipped items add nothing', () => {
    const candidates = [{ barcode: 'a', min_effective_para: 12000 }, { barcode: 'b', min_effective_para: 9900 }]
    expect(selectedTotal([
      { qty: 2, selected: 'b', candidates },
      { qty: 1, selected: '', candidates },
      { qty: 3, selected: 'gone', candidates },
    ])).toBe(19800)
  })
})

