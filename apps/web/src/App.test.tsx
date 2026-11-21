import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test } from 'vitest'
import { App } from './App'
import { copy } from './i18n/sr-Latn'

afterEach(() => { cleanup(); localStorage.clear() })
test('shows an honest empty state and the independence disclaimer', () => {
  render(<App />)
  expect(screen.getByRole('heading', { name: copy.status })).toBeTruthy()
  expect(screen.getByText(copy.disclaimer)).toBeTruthy()
})
test('switches UI script and document language', () => {
  render(<App />)
  fireEvent.click(screen.getByRole('radio', { name: copy.cyrillic }))
  expect(document.documentElement.lang).toBe('sr-Cyrl')
  expect(localStorage.getItem('script')).toBe('cyrl')
  expect(screen.getByRole('heading', { level: 1 }).textContent).toContain('Лакше')
})
