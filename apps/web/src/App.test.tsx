import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test } from 'vitest'
import { App } from './App'
import { I18nProvider } from './i18n/I18nProvider'
import { copy } from './i18n/sr-Latn'

afterEach(() => { cleanup(); localStorage.clear() })
test('shows an honest empty state and the independence disclaimer', () => {
  render(<I18nProvider><App /></I18nProvider>)
  expect(screen.getByRole('heading', { name: copy.status })).toBeTruthy()
  expect(screen.getByText(copy.disclaimer)).toBeTruthy()
})
test('switches UI script and document language', () => {
  render(<I18nProvider><App /></I18nProvider>)
  fireEvent.click(screen.getByRole('radio', { name: copy.cyrillic }))
  expect(document.documentElement.lang).toBe('sr-Cyrl')
  expect(localStorage.getItem('script')).toBe('cyrl')
  expect(screen.getByRole('heading', { level: 1 }).textContent).toContain('Лакше')
})
