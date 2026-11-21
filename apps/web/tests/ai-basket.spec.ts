import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { basket, search, summary } from './fixtures'

const API = 'http://127.0.0.1:8000'
const result = {
  as_of: '2026-11-21', model: 'recorded', items: [
    { phrase: '2 mleka', query: 'mleko', qty: 2, candidates: search.items },
    { phrase: 'još jedno mleko', query: 'mleko', qty: 1, candidates: [search.items[1]] },
    { phrase: 'hleb', query: 'hleb', qty: 1, candidates: [] },
  ],
}

test.beforeEach(async ({ page }) => {
  await page.route(`${API}/api/ai/status`, (route) => route.fulfill({ json: { enabled: true } }))
  await page.route(`${API}/api/ai/basket`, (route) => route.fulfill({ json: result }))
  await page.route(`${API}/api/basket`, (route) => route.fulfill({ json: basket }))
  await page.route(`${API}/graphql`, (route) => route.fulfill({ json: { data: summary } }))
})

for (const mode of ['disabled', 'failed']) {
  test(`${mode} status hides the form and is fetched once`, async ({ page }) => {
    let calls = 0
    await page.route(`${API}/api/ai/status`, (route) => {
      calls++
      return route.fulfill({ status: mode === 'failed' ? 503 : 200, json: { enabled: false } })
    })
    await page.goto('/korpa')
    await expect(page.getByRole('heading', { name: 'Korpa', exact: true })).toBeVisible()
    await expect.poll(() => calls).toBe(1)
    await expect(page.getByRole('textbox', { name: 'Napiši šta kupuješ', exact: true })).toHaveCount(0)
    await page.getByRole('link', { name: 'Idi na pretragu', exact: true }).click()
    await page.getByRole('link', { name: /^Korpa:/ }).click()
    await expect(page.getByRole('heading', { name: 'Korpa', exact: true })).toBeVisible()
    expect(calls).toBe(1)
  })
}

test('keyboard flow reviews candidates and adds two products only on confirmation', async ({ page }, testInfo) => {
  await page.goto('/korpa')
  const input = page.getByRole('textbox', { name: 'Napiši šta kupuješ', exact: true })
  for (let i = 0; i < 40 && !(await input.evaluate((el) => el === document.activeElement)); i++) await page.keyboard.press('Tab')
  await expect(input).toBeFocused()
  await page.keyboard.type('2 mleka, još jedno mleko i hleb')
  await expect(page.getByText('31/300 znakova')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('assistant-form.png'), fullPage: true })
  await testInfo.attach('Form', { path: testInfo.outputPath('assistant-form.png'), contentType: 'image/png' })
  await page.keyboard.press('Tab')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Predloženi proizvodi' })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('korpa'))).toBeNull()
  await expect(page.getByRole('group', { name: '2 mleka' }).getByRole('radio').first()).toBeChecked()
  await expect(page.getByText('Nismo našli proizvod', { exact: false })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Idi na pretragu', exact: true }).first()).toHaveAttribute('href', '/pretraga?q=hleb')
  const violations = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
  expect(violations.violations).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('assistant-result.png'), fullPage: true })
  await testInfo.attach('Result', { path: testInfo.outputPath('assistant-result.png'), contentType: 'image/png' })
  const add = page.getByRole('button', { name: 'Dodaj izabrano u korpu' })
  for (let i = 0; i < 40 && !(await add.evaluate((el) => el === document.activeElement)); i++) await page.keyboard.press('Tab')
  await expect(add).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Cela korpa' })).toBeVisible()
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('korpa') ?? '[]'))).toEqual([
    { barcode: search.items[0].barcode, qty: 2 }, { barcode: search.items[1].barcode, qty: 1 },
  ])
  await expect(add).toBeDisabled()
})

test('429 shows Retry-After in minutes', async ({ page }) => {
  await page.route(`${API}/api/ai/basket`, (route) => route.fulfill({ status: 429,
    headers: { 'Retry-After': '121', 'Access-Control-Expose-Headers': 'Retry-After' }, json: {} }))
  await page.goto('/korpa')
  await page.getByRole('textbox', { name: 'Napiši šta kupuješ', exact: true }).fill('mleko')
  await page.getByRole('button', { name: 'Predloži proizvode' }).click()
  await expect(page.getByRole('status')).toContainText('Pokušaj ponovo za 3 min.')
  await page.getByRole('radio', { name: 'Ћирилица', exact: true }).check()
  await expect(page.getByRole('status')).toContainText('Покушај поново за 3 мин.')
  await expect(page.getByText('5/300 знакова')).toBeVisible()
})

test('pending state blocks repeat requests; validation is inline and unavailable errors are announced', async ({ page }) => {
  let complete: () => void = () => {}
  const pending = new Promise<void>((resolve) => { complete = resolve })
  await page.route(`${API}/api/ai/basket`, async (route) => {
    await pending
    await route.fulfill({ status: 422, json: {} })
  })
  await page.goto('/korpa')
  const input = page.getByRole('textbox', { name: 'Napiši šta kupuješ', exact: true })
  await input.fill('mleko')
  await page.getByRole('button', { name: 'Predloži proizvode' }).click()
  await expect(page.getByRole('button', { name: 'Učitavanje…' })).toBeDisabled()
  await expect(page.locator('form[aria-busy]')).toHaveAttribute('aria-busy', 'true')
  complete()
  await expect(input).toHaveAttribute('aria-invalid', 'true')
  await expect(page.locator('[id$="-error"]')).toContainText('Upiši između 3 i 300 znakova.')
  await page.route(`${API}/api/ai/basket`, (route) => route.fulfill({ status: 503, json: {} }))
  await page.getByRole('button', { name: 'Predloži proizvode' }).click()
  await expect(page.getByRole('status')).toContainText('Pomoćnik trenutno nije dostupan')
})

test('Home never requests assistant status or displays its form', async ({ page }) => {
  let calls = 0
  await page.route(`${API}/api/ai/status`, (route) => { calls++; return route.fulfill({ json: { enabled: true } }) })
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Napiši šta kupuješ' })).toHaveCount(0)
  expect(calls).toBe(0)
})
