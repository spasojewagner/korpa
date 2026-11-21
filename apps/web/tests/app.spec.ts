import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { MILK, basket, categories, product, quality, search, summary } from './fixtures'

// The built site talks to the default local API; every call is answered from fixtures.
const API = 'http://127.0.0.1:8000'

test.beforeEach(async ({ page }) => {
  await page.route(`${API}/api/search?**`, (route) => route.fulfill({ json: search }))
  await page.route(`${API}/api/categories`, (route) => route.fulfill({ json: categories }))
  await page.route(`${API}/api/quality`, (route) => route.fulfill({ json: quality }))
  await page.route(`${API}/api/basket`, (route) => route.fulfill({ json: basket }))
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
  await expect(h1(page)).toContainText('Lakše')
  await expectNoViolations(page)

  await page.getByLabel('Pretraga proizvoda').fill('mleko')
  await page.getByRole('button', { name: 'Traži' }).click()
  await expect(h1(page)).toHaveText('Rezultati za „mleko“')
  await expect(page.getByText('Pronađena su 2 proizvoda')).toBeVisible()
  await expectNoViolations(page)

  await page.getByRole('link', { name: 'Mleko 2,8% 1 l' }).click()
  await expect(h1(page)).toHaveText('Mleko 2,8% 1 l')
  await expect(page.getByText('Najjeftinije')).toHaveCount(1)
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

test('script choice works from the keyboard and survives a reload', async ({ page }) => {
  await page.goto('/o-projektu')
  await page.getByRole('radio', { name: 'Latinica' }).focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.locator('html')).toHaveAttribute('lang', 'sr-Cyrl')
  await expect(h1(page)).toHaveText('О пројекту')
  await page.reload()
  await expect(h1(page)).toHaveText('О пројекту')
})

for (const path of ['/pretraga', '/korpa', '/indeks', '/kvalitet', '/o-projektu', '/nepostoji']) {
  test(`no accessibility violations on ${path}`, async ({ page }) => {
    await page.goto(path)
    await expect(h1(page)).toBeVisible()
    if (path === '/kvalitet') await expect(page.getByRole('table')).toBeVisible()
    await expectNoViolations(page)
  })
}
