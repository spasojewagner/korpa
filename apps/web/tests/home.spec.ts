import { test, expect } from '@playwright/test'
test('home and keyboard script toggle work', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Lakše')
  await page.getByRole('radio', { name: 'Latinica' }).focus()
  await expect(page.getByRole('radio', { name: 'Latinica' })).toBeFocused()
  await page.keyboard.press('ArrowRight')
  await expect(page.locator('html')).toHaveAttribute('lang', 'sr-Cyrl')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Лакше')
})
