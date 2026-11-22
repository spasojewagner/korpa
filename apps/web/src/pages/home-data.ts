import { useEffect, useState } from 'react'
import { fetchCategories, fetchQuality, type Schemas } from '../lib/api'

// Home avoids TanStack Query on purpose (bundle budget); a few small fetches of static JSON are enough.
export function useStatic<T>(load: () => Promise<T>): T | null {
  const [value, setValue] = useState<T | null>(null)
  useEffect(() => {
    let live = true
    load().then((result) => { if (live) setValue(result) }).catch(() => undefined)
    return () => {
      live = false
    }
  }, [load])
  return value
}

export interface HomeData {
  categories: Schemas['CategoryItem'][]
  products: number
  retailers: number
  newest: string | null
}

export async function loadHome(): Promise<HomeData> {
  const [categories, quality] = await Promise.all([fetchCategories(), fetchQuality()])
  const live = quality.retailers.filter((retailer) => (retailer.rows_valid ?? 0) > 0)
  const dates = live.map((retailer) => retailer.list_date).filter((date): date is string => !!date)
  return {
    categories: categories.filter((item) => item.n_products > 0),
    products: categories.reduce((sum, item) => sum + item.n_products, 0),
    retailers: live.length,
    newest: dates.sort().at(-1) ?? null,
  }
}

