import { afterEach, describe, expect, test } from 'vitest'
import { monthlyLows } from '../pages/Product'
import { toTotals } from '../pages/Basket'
import { parseSearch } from '../router'
import { MAX_ITEMS, basket } from './basket'

afterEach(() => basket.clear())

describe('basket store', () => {
  test('adds once, clamps quantity, removes and persists', () => {
    basket.add('8600000000001')
    basket.add('8600000000001')
    basket.setQty('8600000000001', 250)
    expect(JSON.parse(localStorage.getItem('korpa') ?? '[]')).toEqual([{ barcode: '8600000000001', qty: 99 }])
    basket.remove('8600000000001')
    expect(localStorage.getItem('korpa')).toBe('[]')
  })
  test('refuses items past the limit', () => {
    for (let i = 0; i < MAX_ITEMS; i++) basket.add(String(i).padStart(13, '0'))
    expect(basket.add('9999999999999')).toBe(false)
  })
})

test('search params are bounded and typed', () => {
  expect(parseSearch({ q: '  mleko ', kategorija: '3' })).toEqual({ q: 'mleko', kategorija: 3 })
  expect(parseSearch({ q: 8600000000001, kategorija: 99 })).toEqual({ q: '8600000000001', kategorija: undefined })
  expect(parseSearch({ q: 'x'.repeat(200) }).q).toHaveLength(100)
  expect(parseSearch({})).toEqual({ q: undefined, kategorija: undefined })
})

test('history uses the lowest regular price of each month', () => {
  expect(monthlyLows([
    { month: '2026-01-01', minRegularPara: 200 },
    { month: '2026-02-01', minRegularPara: 250 },
  ])).toEqual([{ month: '2026-01-01', para: 200 }, { month: '2026-02-01', para: 250 }])
})

test('basket response maps to totals with missing counts and dates', () => {
  const totals = toTotals({
    as_of: '2026-11-21',
    retailers: [{ id: 1, name: 'Alfa', slug: 'alfa', formats: [{
      id: 7, name: 'Hiper', total_para: 1000, found_barcodes: ['1'], missing_barcodes: ['2', '3'],
      complete: false, rank: 1, list_date_min: null, list_date_max: null,
    }] }],
  })
  expect(totals).toEqual([{ key: '7', retailer: 'Alfa', format: 'Hiper', totalPara: 1000, complete: false, missing: 2, listDate: '2026-11-21' }])
})
