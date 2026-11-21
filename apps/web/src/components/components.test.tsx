import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import axe from 'axe-core'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { I18nProvider, createI18n, type Script } from '../i18n/I18nProvider'
import { transliterate } from '../i18n/transliterate'
import { daysSince, formatDate, formatPrice } from '../lib/format'
import {
  BasketSummary, Badge, Price, PriceComparison, ProductCard, QuantityStepper, ScriptToggle,
  SearchForm, SiteFooter, SourceDate, Sparkline, StateView, type BasketTotal, type FormatPrice,
} from '.'

const today = new Date(2026, 10, 21)
const nbsp = (text: string | null) => (text ?? '').replace(/\u00a0|\u202f/g, ' ')
const ui = (node: ReactNode, script: Script = 'latn') =>
  render(<I18nProvider initial={script}>{node}</I18nProvider>)

afterEach(() => { cleanup(); localStorage.clear() })

describe('format', () => {
  test('para to RSD, dates and day differences', () => {
    expect(nbsp(formatPrice(12999))).toBe('129,99 RSD')
    expect(nbsp(formatPrice(129900))).toBe('1.299,00 RSD')
    expect(formatDate('2026-11-19')).toBe('19.11.2026.')
    expect(daysSince('2026-11-19', today)).toBe(2)
  })
})

describe('i18n', () => {
  test('transliterates digraphs and keeps data in vars untouched', () => {
    expect(transliterate('Ljubljana Njegoš Džak')).toBe('Љубљана Његош Џак')
    const { t } = createI18n('cyrl')
    expect(t('sourceDate', { date: '19.11.2026.' })).toBe('Ценовник од 19.11.2026.')
    expect(t('perUnit', { price: '1 RSD', unit: 'kg' })).toBe('1 RSD/kg')
  })
  test('Serbian plural forms', () => {
    const { tp } = createI18n('latn')
    expect([1, 2, 5, 21, 22].map((n) => tp('formats', n))).toEqual([
      'u 1 formatu', 'u 2 formata', 'u 5 formata', 'u 21 formatu', 'u 22 formata',
    ])
    expect(tp('missing', 3)).toBe('Nedostaju 3 proizvoda')
  })
})

describe('price and date', () => {
  test('discount shows the regular price with a spoken label', () => {
    ui(<Price para={9999} regularPara={12999} unitPara={19998} unit="kg" />)
    const regular = document.querySelector('del')
    expect(nbsp(regular?.textContent ?? '')).toBe('redovna cena: 129,99 RSD')
    expect(screen.getByText(/99,99/).tagName).toBe('STRONG')
    expect(nbsp(screen.getByText(/\/kg/).textContent)).toBe('199,98 RSD/kg')
  })
  test('stale price list is flagged with text', () => {
    ui(<><SourceDate date="2026-11-20" today={today} /><SourceDate date="2026-11-10" today={today} /></>)
    expect(screen.getAllByText(/Cenovnik od/)).toHaveLength(2)
    expect(screen.getAllByText('Podaci stariji od 3 dana')).toHaveLength(1)
  })
})

const rows: FormatPrice[] = [
  { formatId: 1, retailer: 'Beta', format: 'Market', para: 15000, listDate: '2026-11-20' },
  { formatId: 2, retailer: 'Alfa', format: 'Hiper', para: 12000, regularPara: 14000, discountTo: '2026-11-30', listDate: '2026-11-20' },
  { formatId: 3, retailer: 'Gama', format: 'Diskont', para: 12000, listDate: '2026-11-20' },
]

test('price comparison: cheapest first, ties share the badge, discount end date', () => {
  ui(<PriceComparison rows={rows} unit="l" today={today} />)
  const names = screen.getAllByRole('rowheader').map((cell) => cell.querySelector('span')?.textContent)
  expect(names).toEqual(['Alfa', 'Gama', 'Beta'])
  expect(screen.getAllByText('Najjeftinije')).toHaveLength(2)
  expect(screen.getByText('Sniženo do 30.11.2026.')).toBeTruthy()
})

test('basket: partial baskets are listed apart and never marked cheapest', () => {
  const totals: BasketTotal[] = [
    { key: 'a', retailer: 'Alfa', format: 'Hiper', totalPara: 90000, complete: false, missing: 2, listDate: '2026-11-20' },
    { key: 'b', retailer: 'Beta', format: 'Market', totalPara: 120000, complete: true, missing: 0, listDate: '2026-11-20' },
    { key: 'c', retailer: 'Gama', format: 'Diskont', totalPara: 110000, complete: true, missing: 0, listDate: '2026-11-20' },
  ]
  ui(<BasketSummary totals={totals} today={today} />)
  const [complete, partial] = screen.getAllByRole('list')
  expect(within(complete).getAllByRole('listitem')[0].textContent).toContain('Gama')
  expect(within(complete).getByText('Najjeftinije')).toBeTruthy()
  expect(within(partial).queryByText('Najjeftinije')).toBeNull()
  expect(within(partial).getByText('Nedostaju 2 proizvoda')).toBeTruthy()
})

test('quantity stepper clamps and labels buttons with the product name', () => {
  const onChange = vi.fn()
  ui(<QuantityStepper value={1} onChange={onChange} name="Mleko 1 l" />)
  expect((screen.getByRole('button', { name: 'Smanji količinu: Mleko 1 l' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Povećaj količinu: Mleko 1 l' }))
  expect(onChange).toHaveBeenLastCalledWith(2)
  const input = screen.getByLabelText('Količina: Mleko 1 l')
  fireEvent.change(input, { target: { value: '250' } })
  fireEvent.blur(input)
  expect(onChange).toHaveBeenLastCalledWith(25)
})

test('search form trims the query and script toggle switches the document language', () => {
  const onSearch = vi.fn()
  ui(<><SearchForm onSearch={onSearch} /><ScriptToggle /></>)
  fireEvent.change(screen.getByLabelText('Pretraga proizvoda'), { target: { value: '  mleko ' } })
  fireEvent.submit(screen.getByRole('search'))
  expect(onSearch).toHaveBeenCalledWith('mleko')
  fireEvent.click(screen.getByRole('radio', { name: 'Ћирилица' }))
  expect(document.documentElement.lang).toBe('sr-Cyrl')
  expect(screen.getByLabelText('Претрага производа')).toBeTruthy()
})

test('sparkline caption states lowest and highest month', () => {
  ui(<Sparkline points={[{ month: '2026-01-01', para: 10000 }, { month: '2026-02-01', para: 12000 }, { month: '2026-03-01', para: 11000 }]} />)
  expect(nbsp(screen.getByText(/Najniža/).textContent)).toBe('Najniža cena 100,00 RSD (01.2026.), najviša 120,00 RSD (02.2026.).')
})

test('state views use status and alert roles', () => {
  const onRetry = vi.fn()
  ui(<><StateView kind="loading" /><StateView kind="error" onRetry={onRetry} /></>)
  expect(screen.getByRole('status').getAttribute('aria-busy')).toBe('true')
  fireEvent.click(within(screen.getByRole('alert')).getByRole('button', { name: 'Pokušaj ponovo' }))
  expect(onRetry).toHaveBeenCalled()
})

test('all components together have no axe violations', async () => {
  const { container } = ui(<main>
    <h1>Test</h1>
    <SearchForm />
    <ScriptToggle />
    <ProductCard href="/proizvod/8600000000001" onAdd={() => {}} today={today} product={{
      barcode: '8600000000001', name: 'Mleko 2,8% 1 l', brand: 'Imlek', unit: 'l', minPara: 12000,
      maxPara: 15000, nFormats: 3, anyDiscount: true, listDate: '2026-11-20' }} />
    <PriceComparison rows={rows} unit="l" today={today} />
    <QuantityStepper value={2} onChange={() => {}} name="Mleko 2,8% 1 l" />
    <BasketSummary today={today} totals={[{ key: 'x', retailer: 'Alfa', format: 'Hiper', totalPara: 1000, complete: true, missing: 0, listDate: '2026-11-20' }]} />
    <Sparkline points={[{ month: '2026-01-01', para: 1 }, { month: '2026-02-01', para: 2 }]} />
    <Badge variant="increase" />
    <StateView kind="empty" />
    <SiteFooter />
  </main>)
  // jsdom cannot compute colors; contrast is verified in docs/design and by Playwright + axe in the browser.
  const results = await axe.run(container, { rules: { 'color-contrast': { enabled: false }, region: { enabled: false } } })
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([])
})
