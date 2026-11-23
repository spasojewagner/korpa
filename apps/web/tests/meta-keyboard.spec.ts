import { expect } from '@playwright/test'
import { test } from './security'
import { MILK, basket, categories, priceIndex, product, quality, search, signals, summary } from './fixtures'

const API = 'https://korpa-api.onrender.com'
const paths = ['/', '/pretraga?q=mleko', `/proizvod/${MILK}`, '/korpa', '/podaci',
  '/podaci/indeks', '/podaci/kvalitet', '/podaci/api', '/o-projektu', '/nepostoji']

test.beforeEach(async ({ page }) => {
  const responses = { categories, quality, index: priceIndex, signals, search, basket, 'ai/status': { enabled: false } }
  await page.route(`${API}/**`, (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/graphql') return route.fulfill({ json: { data: String(route.request().postData()).includes('ProductDetail') ? product : summary } })
    const key = path.replace('/api/', '') as keyof typeof responses
    if (!(key in responses)) throw new Error(`Unexpected fixture request: ${path}`)
    return route.fulfill({ json: responses[key] })
  })
  for (const [name, json] of Object.entries({ categories, quality, index: priceIndex, signals })) {
    await page.route(`**/data/${name}.json`, (route) => route.fulfill({ json }))
  }
})

test('every route sets distinct metadata and exposes the skip link before its content', async ({ page }) => {
  const descriptions = new Set<string>()
  const titles = new Set<string>()
  for (const path of paths) {
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    const description = await page.locator('meta[name="description"]').getAttribute('content')
    expect(description).toBeTruthy()
    descriptions.add(description!)
    titles.add(await page.title())
    await page.keyboard.press('Tab')
    await expect(page.getByRole('link', { name: 'Pređi na sadržaj' })).toBeFocused()
    await expect(page.getByRole('link', { name: 'Pređi na sadržaj' })).toBeVisible()
    await page.keyboard.press('Enter')
    await expect(page.locator('main')).toBeFocused()
    await page.keyboard.press('Tab')
    const focus = await page.evaluate(() => {
      const element = document.activeElement
      if (!(element instanceof HTMLElement)) return null
      const style = getComputedStyle(element)
      return { outline: style.outlineStyle, width: style.outlineWidth }
    })
    expect(focus?.outline).toBe('solid')
    expect(focus?.width).toBe('3px')
  }
  expect(descriptions.size).toBe(paths.length)
  expect(titles.size).toBe(paths.length)
})

test('crawler files are static documents instead of the SPA fallback', async ({ request }) => {
  const robots = await request.get('/robots.txt')
  expect(robots.headers()['content-type']).toContain('text/plain')
  expect(await robots.text()).toContain('Sitemap: https://ai-korpa.vercel.app/sitemap.xml')
  const sitemap = await request.get('/sitemap.xml')
  expect(sitemap.headers()['content-type']).toContain('xml')
  for (const path of ['/podaci', '/podaci/indeks', '/podaci/kvalitet', '/podaci/api', '/o-projektu']) {
    expect(await sitemap.text()).toContain(`<loc>https://ai-korpa.vercel.app${path}</loc>`)
  }
})

test('removing the last basket item returns focus to its primary action', async ({ page }) => {
  await page.addInitScript((barcode) => localStorage.setItem('korpa', JSON.stringify([{ barcode, qty: 1 }])), MILK)
  await page.goto('/korpa')
  await page.getByRole('button', { name: /^Ukloni/ }).click()
  await expect(page.locator('main')).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Idi na pretragu', exact: true })).toBeFocused()
})
