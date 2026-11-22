import { mkdir, writeFile, appendFile } from 'node:fs/promises'
import { preview } from 'vite'
import lighthouse from 'lighthouse'
import { launch } from 'chrome-launcher'
import { chromium } from '@playwright/test'
import { MILK, basket, categories, priceIndex, quality, search, signals, summary } from '../tests/fixtures.ts'

const origin = 'http://127.0.0.1:4174'
const api = 'https://korpa-api.onrender.com'
const paths = ['/', '/pretraga?q=mleko', '/korpa', '/podaci', '/podaci/indeks']
const thresholds = { performance: 90, accessibility: 100, 'best-practices': 95, seo: 95 }
const output = new URL('../lighthouse-results/', import.meta.url)
await mkdir(output, { recursive: true })
const server = await preview({ preview: { host: '127.0.0.1', port: 4174, strictPort: true } })
let chrome
let browser
const rows = []
let failed = false
try {
  chrome = await launch({ chromePath: chromium.executablePath(), chromeFlags: ['--headless=new', '--disable-gpu', '--no-sandbox'] })
  browser = await chromium.connectOverCDP(`http://127.0.0.1:${chrome.port}`)
  const context = browser.contexts()[0]
  await context.addInitScript((barcode) => localStorage.setItem('korpa', JSON.stringify([{ barcode, qty: 1 }])), MILK)
  const responses = { categories, quality, index: priceIndex, signals, basket, search, 'ai/status': { enabled: false } }
  // Intercept at browser-context level, including pages Lighthouse creates. Never contact the live API.
  await context.route(`${api}/**`, (route) => {
    const path = new URL(route.request().url()).pathname
    const json = path === '/graphql' ? { data: summary } : responses[path.replace('/api/', '')]
    if (!json) throw new Error(`Unmocked API request: ${path}`)
    return route.fulfill({ json, headers: { 'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'content-type, accept' } })
  })
  await context.route(`${origin}/data/*.json`, (route) => {
    const name = new URL(route.request().url()).pathname.split('/').pop().replace('.json', '')
    return route.fulfill({ json: responses[name] })
  })
  for (const [index, path] of paths.entries()) {
    const result = await lighthouse(origin + path, {
      port: chrome.port, output: ['json', 'html'], logLevel: 'error',
      onlyCategories: Object.keys(thresholds),
    })
    if (!result || result.lhr.runtimeError) throw new Error(`Lighthouse failed on ${path}: ${result?.lhr.runtimeError?.message}`)
    await writeFile(new URL(`${index}.json`, output), result.report[0])
    await writeFile(new URL(`${index}.html`, output), result.report[1])
    const scores = Object.fromEntries(Object.entries(result.lhr.categories).map(([key, value]) => [key, Math.round(value.score * 100)]))
    rows.push(`| ${path} | ${Object.keys(thresholds).map((key) => scores[key]).join(' | ')} |`)
    console.log(path, scores)
    for (const [key, minimum] of Object.entries(thresholds)) {
      if (result.lhr.categories[key].score * 100 < minimum) failed = true
    }
  }
} finally {
  if (browser) await browser.close()
  if (chrome) await chrome.kill()
  await new Promise((resolve, reject) => server.httpServer.close((error) => error ? reject(error) : resolve()))
  const report = ['## Lighthouse (mobile, mocked data)', '', '| Page | Performance | Accessibility | Best practices | SEO |', '| --- | ---: | ---: | ---: | ---: |', ...rows, '', 'Required: performance ≥ 90, accessibility = 100, best practices ≥ 95, SEO ≥ 95.', ''].join('\n')
  await writeFile(new URL('scores.md', output), report)
  if (process.env.GITHUB_STEP_SUMMARY) await appendFile(process.env.GITHUB_STEP_SUMMARY, report)
}
if (failed) throw new Error('Lighthouse thresholds failed; see lighthouse-results/scores.md and reports')
