import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { MILK, basket, categories, priceIndex, product, quality, search, signals, summary } from './fixtures'

const API = 'http://127.0.0.1:8000'
const pages = [
  ['search', '/pretraga?q=mleko', 'Pronađena su 2 proizvoda'],
  ['product', `/proizvod/${MILK}`, 'Cene u prodavnicama'],
  ['basket', '/korpa', 'Cela korpa'],
  ['index', '/podaci/indeks', 'Kratak pregled'],
  ['quality', '/podaci/kvalitet', 'Verovatne greške u cenama:'],
  ['about', '/o-projektu', 'O projektu'],
  ['not-found', '/nepostoji', 'Stranica nije pronađena'],
] as const

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-11-22T12:00:00+01:00'))
  await page.addInitScript((barcode) => localStorage.setItem('korpa', JSON.stringify([{ barcode, qty: 1 }])), MILK)
  const responses = { 'ai/status': { enabled: false }, categories, quality, basket, index: priceIndex, signals }
  for (const [path, json] of Object.entries(responses)) {
    await page.route(`${API}/api/${path}`, (route) => route.fulfill({ json }))
  }
  for (const [path, json] of Object.entries({ categories, quality, index: priceIndex, signals })) {
    await page.route(`**/data/${path}.json`, (route) => route.fulfill({ json }))
  }
  await page.route(`${API}/api/search?**`, (route) => route.fulfill({ json: search }))
  await page.route(`${API}/graphql`, (route) => {
    const query = String((route.request().postDataJSON() as { query?: string }).query)
    return route.fulfill({ json: { data: query.includes('ProductDetail') ? product : summary } })
  })
})

async function accessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
  expect(results.violations).toEqual([])
}

for (const width of [1440, 390]) {
  for (const [name, path, ready] of pages) {
    test(`${name} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(path)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      await expect(page.locator('main').getByText(ready, { exact: true }).first()).toBeVisible()
      await page.evaluate(() => document.fonts.ready)
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
      await accessible(page)
      if (process.env.SCREENSHOT_DIR) {
        await page.screenshot({ path: `${process.env.SCREENSHOT_DIR}/${name}-${width}.png`, fullPage: true, animations: 'disabled' })
      }
    })
  }
}

test('category pills preserve the query and expose their selection to the keyboard', async ({ page }) => {
  await page.goto('/pretraga?q=mleko')
  const category = page.getByRole('button', { name: 'Mleko i mlečni proizvodi', exact: true })
  await category.focus()
  await page.keyboard.press('Enter')
  await expect(category).toHaveAttribute('aria-pressed', 'true')
  expect(new URL(page.url()).searchParams.get('q')).toBe('mleko')
  expect(new URL(page.url()).searchParams.get('kategorija')).toBe('2')
  const size = await category.boundingBox()
  expect(size?.height).toBeGreaterThanOrEqual(44)
  await page.getByRole('button', { name: 'Sve kategorije', exact: true }).click()
  await expect(category).toHaveAttribute('aria-pressed', 'false')
  expect(new URL(page.url()).searchParams.has('kategorija')).toBe(false)
})

test('product prices stay inside their card on small phones', async ({ page }) => {
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/proizvod/${MILK}`)
    const section = page.getByRole('region', { name: 'Cene u prodavnicama' })
    await expect(section.getByRole('table')).toBeVisible()
    const bounds = await section.boundingBox()
    for (const cell of await section.getByRole('cell').all()) {
      const box = await cell.boundingBox()
      expect(box && bounds && box.x + box.width).toBeLessThanOrEqual((bounds?.x ?? 0) + (bounds?.width ?? 0))
    }
  }
})

test('quality table scrolls from the keyboard on phones', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/podaci/kvalitet')
  const region = page.getByRole('region', { name: 'Poslednje preuzimanje po trgovcu' })
  await expect(region.getByRole('table')).toBeVisible()
  await region.focus()
  await expect(region).toBeFocused()
  await page.keyboard.press('ArrowRight')
  await expect.poll(() => region.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0)
})

test('loading and empty search states remain accessible', async ({ page }) => {
  let release!: () => void
  const pending = new Promise<void>((resolve) => { release = resolve })
  await page.route(`${API}/api/search?**`, async (route) => {
    await pending
    await route.fulfill({ json: { ...search, items: [], total: 0 } })
  })
  await page.goto('/pretraga?q=mleko')
  await expect(page.locator('[aria-busy="true"]')).toContainText('Učitavanje…')
  await accessible(page)
  release()
  await expect(page.getByText('Nema rezultata', { exact: true })).toBeVisible()
  await accessible(page)
})

for (const offline of [false, true]) {
  test(`${offline ? 'offline' : 'error'} search state offers a working retry`, async ({ page }) => {
    let failed = true
    await page.route(`${API}/api/search?**`, (route) => failed
      ? offline ? route.abort('internetdisconnected') : route.fulfill({ status: 500, body: '' })
      : route.fulfill({ json: search }))
    await page.goto('/pretraga?q=mleko')
    const alert = page.getByRole('alert')
    await expect(alert).toContainText(offline ? 'Niste povezani na internet' : 'Nešto nije u redu')
    await expect(alert.getByRole('button')).toHaveCount(1)
    await accessible(page)
    failed = false
    await alert.getByRole('button', { name: 'Pokušaj ponovo' }).click()
    await expect(page.getByRole('link', { name: 'Mleko 2,8% 1 l', exact: true })).toBeVisible()
  })
}

test('empty basket offers a primary path to search', async ({ page }) => {
  await page.addInitScript(() => localStorage.removeItem('korpa'))
  await page.goto('/korpa')
  const searchLink = page.getByRole('link', { name: 'Idi na pretragu', exact: true })
  await expect(page.getByText('Korpa je još prazna.', { exact: false })).toBeVisible()
  await accessible(page)
  await searchLink.click()
  await expect(page).toHaveURL(/\/pretraga$/)
})

