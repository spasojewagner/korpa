import { useSyncExternalStore } from 'react'

// The basket lives only in this browser: barcodes and quantities, no personal data.
export interface BasketItem {
  barcode: string
  qty: number
}

const KEY = 'korpa'
export const MAX_ITEMS = 50
export const MAX_QTY = 99

const valid = (item: unknown): item is BasketItem =>
  typeof item === 'object' && item !== null &&
  /^[0-9]{13}$/.test(String((item as BasketItem).barcode)) &&
  Number.isInteger((item as BasketItem).qty) && (item as BasketItem).qty >= 1 && (item as BasketItem).qty <= MAX_QTY

function read(): BasketItem[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter(valid).slice(0, MAX_ITEMS) : []
  } catch {
    return []
  }
}

let items: BasketItem[] = read()
const listeners = new Set<() => void>()

function write(next: BasketItem[]) {
  items = next
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Storage unavailable: the basket lasts for this visit only.
  }
  listeners.forEach((listener) => listener())
}

function onStorage(event: StorageEvent) {
  if (event.key !== KEY) return
  items = read()
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  if (listeners.size === 0) window.addEventListener('storage', onStorage)
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) window.removeEventListener('storage', onStorage)
  }
}

export const basket = {
  /** Returns false when the basket is full. */
  add(barcode: string): boolean {
    if (items.some((item) => item.barcode === barcode)) return true
    if (items.length >= MAX_ITEMS) return false
    write([...items, { barcode, qty: 1 }])
    return true
  },
  setQty(barcode: string, qty: number) {
    const clamped = Math.min(MAX_QTY, Math.max(1, Math.round(qty)))
    write(items.map((item) => (item.barcode === barcode ? { ...item, qty: clamped } : item)))
  },
  remove(barcode: string) {
    write(items.filter((item) => item.barcode !== barcode))
  },
  clear() {
    write([])
  },
}

export function useBasket(): BasketItem[] {
  return useSyncExternalStore(subscribe, () => items, () => items)
}
