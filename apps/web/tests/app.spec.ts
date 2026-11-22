import { test } from './security'
import AxeBuilder from '@axe-core/playwright'
import { expect, type Page } from '@playwright/test'
import { MILK, basket, categories, priceIndex, product, quality, search, signals, summary } from './fixtures'

// The production API origin is allowed by CSP; every call is answered from fixtures.
const API = 'https://korpa-api.onrender.com'

test.beforeEach(async ({ page }) => {
  await page.route(`${API}/api/ai/status`, (route) => route.fulfill({ json: { enabled: false } }))
  await page.route(`${API}/api/search?**`, (route) => route.fulfill({ json: search }))
  await page.route(`${API}/api/categories`, (route) => route.fulfill({ json: categories }))
  await page.route(`${API}/api/quality`, (route) => route.fulfill({ json: quality }))
  await page.route(`${API}/api/basket`, (route) => route.fulfill({ json: basket }))
  await page.route(`${API}/api/index`, (route) => route.fulfill({ json: priceIndex }))
  await page.route(`${API}/api/signals`, (route) => route.fulfill({ json: signals }))
  await page.route(`${API}/graphql`, (route) => {
    const query = String((route.request().postDataJSON() as { query?: string }).query)
    return route.fulfill({ json: { data: query.includes('ProductDetail') ? product : summary } })
  })
})

async function expectNoViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([])
}

const h1 = (page: Page) => page.getByRole('heading', { level: 1 })

test('search → product → basket ranks retailers', async ({ page }) => {
  await page.goto('/')
  await expect(h1(page)).toContainText('Ista korpa.')
  await expectNoViolations(page)

  await page.getByLabel('Pretraga proizvoda').fill('mleko')
  await page.getByRole('button', { name: 'Traži' }).click()
  await expect(h1(page)).toHaveText('Rezultati za „mleko“')
  await expect(page.getByText('Pronađena su 2 proizvoda')).toBeVisible()
  await expectNoViolations(page)

  await page.getByRole('link', { name: 'Mleko 2,8% 1 l' }).click()
  await expect(h1(page)).toHaveText('Mleko 2,8% 1 l')
  await expect(page.getByText('Najjeftinije')).toHaveCount(1)
  // Para must never be rounded away (browser locale data has 0 decimals for RSD).
  await expect(page.getByText(/^139,99\sRSD$/)).toBeVisible()
  await expect(page.getByText('Sniženo do 30.11.2026.')).toBeVisible()
  await expectNoViolations(page)

  await page.getByRole('button', { name: 'Dodaj u korpu' }).click()
  await expect(page.getByRole('link', { name: /Korpa: 1 proizvod/ })).toBeVisible()
  await page.getByRole('link', { name: 'Idi u korpu' }).click()
  await expect(h1(page)).toHaveText('Korpa')
  await expect(page.getByRole('heading', { name: 'Cela korpa' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Nepotpune korpe' })).toBeVisible()
  await expect(page.getByText('Nedostaje 1 proizvod')).toBeVisible()
  await expectNoViolations(page)
})

test('keyboard only: add to basket and raise the quantity', async ({ page }) => {
  await page.goto(`/proizvod/${MILK}`)
  await expect(h1(page)).toBeVisible()
  const add = page.getByRole('button', { name: 'Dodaj u korpu' })
  for (let i = 0; i < 40 && !(await add.evaluate((element) => element === document.activeElement)); i++) {
    await page.keyboard.press('Tab')
  }
  await expect(add).toBeFocused()
  await page.keyboard.press('Enter')
  const quantity = page.getByLabel('Količina: Mleko 2,8% 1 l')
  await expect(quantity).toBeFocused()
  await page.keyboard.press('ArrowUp')
  await expect(quantity).toHaveValue('2')
})

test('split basket shows dated savings and keyboard expandable items with axe', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 })
  await page.addInitScript((barcode) => {
    localStorage.setItem('korpa', JSON.stringify([{ barcode, qty: 2 }, { barcode: '8600000000002', qty: 1 }]))
  }, MILK)
  await page.route(`${API}/api/basket`, (route) => route.fulfill({ json: {
    ...basket,
    split: { total_para: 40997, saving_vs_best_para: 3000, n_formats: 2, items: [
      { barcode: MILK, format: { id: 1, name: 'Alfa Hiper' }, price_para: 13999, list_date: '2026-11-20' },
      { barcode: '8600000000002', format: { id: 2, name: 'Beta Market' }, price_para: 12999, list_date: '2026-11-19' },
    ] },
  } }))
  await page.goto('/korpa')
  const card = page.getByRole('region', { name: 'Najjeftinije po stavci' })
  await expect(card).toContainText(/409,97\sRSD/)
  await expect(card).toContainText(/30,00\sRSD/)
  await expect(card).toContainText('Kupovina u 2 formata prodavnica')
  await expect(card).toContainText('obilazak više prodavnica')
  await expect(card).toContainText('19.11.2026.')
  await expect(card.getByRole('list')).toBeHidden()
  await expectNoViolations(page)
  const disclosure = card.locator('summary')
  await disclosure.focus()
  await page.keyboard.press('Enter')
  await expect(card.getByRole('listitem')).toHaveCount(2)
  await expect(card.getByRole('listitem').first()).toContainText(/2 × 139,99\sRSD/)
  await expect(card.getByRole('listitem').last()).toContainText('Beta Market')
  await expectNoViolations(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320)
  await page.keyboard.press('Enter')
  await expect(card.getByRole('list')).toBeHidden()
})

test('split basket is hidden for unavailable items and explains absent single-format comparison', async ({ page }) => {
  await page.addInitScript((barcode) => {
    localStorage.setItem('korpa', JSON.stringify([{ barcode, qty: 1 }]))
  }, MILK)
  await page.route(`${API}/api/basket`, (route) => route.fulfill({ json: { ...basket, split: null } }))
  await page.goto('/korpa')
  await expect(page.getByRole('heading', { name: 'Cela korpa' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Najjeftinije po stavci' })).toHaveCount(0)
  await page.route(`${API}/api/basket`, (route) => route.fulfill({ json: {
    ...basket, split: { ...basket.split, saving_vs_best_para: null },
  } }))
  await page.reload()
  const card = page.getByRole('region', { name: 'Najjeftinije po stavci' })
  await expect(card).toContainText('Nijedan format nema celu korpu')
  await expectNoViolations(page)
})

test('script choice works from the keyboard and survives a reload', async ({ page }) => {
  await page.goto('/o-projektu')
  await page.getByRole('radio', { name: 'Latinica' }).focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.locator('html')).toHaveAttribute('lang', 'sr-Cyrl')
  await expect(h1(page)).toHaveText('О пројекту')
  await page.reload()
  await expect(h1(page)).toHaveText('О пројекту')
})

for (const path of ['/pretraga', '/korpa', '/indeks', '/kvalitet', '/podaci', '/podaci/api', '/o-projektu', '/nepostoji']) {
  test(`no accessibility violations on ${path}`, async ({ page }) => {
    await page.goto(path)
    await expect(h1(page)).toBeVisible()
    if (path === '/kvalitet') {
      await expect(page.getByRole('table')).toBeVisible()
      await expect(page.getByText('Verovatne greške u cenama:')).toBeVisible()
    }
    await expectNoViolations(page)
  })
}

test('price index: overall value, categories, signals filter', async ({ page }) => {
  await page.goto('/indeks')
  await expect(page).toHaveURL(/\/podaci\/indeks$/)
  await expect(h1(page)).toHaveText('Indeks cena')
  await expect(page.getByText(/^101,4$/)).toBeVisible()
  await expect(page.getByText('+1,4 %').first()).toBeVisible()
  const notes = page.getByRole('region', { name: 'Kratak pregled' })
  await expect(notes.getByRole('listitem')).toHaveText('Ukupni indeks je 101,4, što je rast od 1,4 % od novembra 2026.')
  await expect(notes).toContainText('Automatski tekst')
  await expect(page.getByRole('row', { name: /Mleko i mlečni proizvodi/ })).toContainText('97,5')
  await expect(page.getByRole('row', { name: /Sirće/ })).toContainText('premalo proizvoda')
  await expect(page.getByRole('listitem').filter({ hasText: 'Redovna cena porasla je za +27,0 %' })).toBeVisible()
  await page.getByRole('button', { name: 'Odstupanje od drugih' }).click()
  await expect(page.getByRole('button', { name: 'Odstupanje od drugih' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText(/1,56× srednje cene/)).toBeVisible()
  await expect(page.getByText(/porasla je za/)).toHaveCount(0)
  await expectNoViolations(page)
})

test('home categories open category browsing', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: /Mleko i mlečni proizvodi/ }).click()
  await expect(h1(page)).toHaveText('Mleko i mlečni proizvodi')
  await expect(page.getByText('Pronađena su 2 proizvoda')).toBeVisible()
  await expectNoViolations(page)
})

test('discount after jump filter exposes its method and dates with axe', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/podaci/indeks')
  const filter = page.getByRole('button', { name: 'Sniženje posle skoka redovne cene', exact: true })
  await filter.focus()
  await page.keyboard.press('Enter')
  await expect(filter).toHaveAttribute('aria-pressed', 'true')
  const signal = page.getByRole('listitem').filter({ hasText: 'Signal: redovna cena' })
  await expect(signal).toHaveCount(1)
  await expect(signal).toContainText('najmanje 20 %')
  await expect(signal).toContainText('najmanje 98 %')
  await expect(signal).toContainText('15.11.2026.')
  await expect(signal).toContainText('21.11.2026.')
  await expect(page.getByText(/1,56× srednje cene/)).toHaveCount(0)
  await expectNoViolations(page)
})

test('name variants are informational and dated with axe', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/podaci/kvalitet')
  const block = page.getByRole('region', { name: 'Isti barkod, različiti nazivi' })
  await expect(block).toContainText('nisu greška')
  await expect(block).toContainText(/50\s*%/)
  await expect(block).toContainText('21.11.2026.')
  await expect(block).toContainText(MILK)
  await expect(block).toContainText('Alfa: MLEKO 2,8% 1L IMLEK')
  await expect(block).toContainText('Beta: Mleko 2,8% 1 l')
  await expectNoViolations(page)
})

test('data area has its own navigation and keeps old addresses', async ({ page }) => {
  await page.goto('/kvalitet')
  await expect(page).toHaveURL(/\/podaci\/kvalitet$/)
  const tabs = page.getByRole('navigation', { name: 'Meni podataka' })
  await expect(tabs.getByRole('link', { name: 'Kvalitet' })).toHaveAttribute('aria-current', 'page')
  await tabs.getByRole('link', { name: 'Pregled' }).click()
  await expect(h1(page)).toHaveText('Podaci o cenama namirnica')
  await expect(page.getByText('redova cena prošlo je proveru')).toBeVisible()
  await page.getByRole('link', { name: 'Kupovina' }).click()
  await expect(h1(page)).toContainText('Ista korpa.')
  await expect(page.getByRole('navigation', { name: 'Glavni meni' })).toBeVisible()
})

test('no sideways scroll on small phones', async ({ page }) => {
  for (const path of ['/', '/podaci', '/podaci/api', '/korpa']) {
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 800 })
      await page.goto(path)
      await expect(page.locator('h1')).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth), `${path} at ${width}`).toBeLessThanOrEqual(width)
    }
  }
})
