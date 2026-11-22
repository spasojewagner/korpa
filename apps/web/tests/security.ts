import { test as base, expect } from '@playwright/test'

// Automatic fixture: every e2e page must obey the production CSP, including error states.
export const test = base.extend<{ cspGuard: void }>({
  cspGuard: [async ({ page }, runTest) => {
    const errors: string[] = []
    page.on('console', (message) => {
      if (/content.security.policy|violat.*(?:directive|policy)|refused to (?:load|connect|execute|apply|frame)/i.test(message.text())) errors.push(message.text())
    })
    await page.addInitScript(() => {
      document.addEventListener('securitypolicyviolation', (event) => {
        console.error(`Content Security Policy: ${event.violatedDirective} ${event.blockedURI}`)
      })
    })
    await runTest()
    expect(errors, 'CSP violations').toEqual([])
  }, { auto: true }],
})
