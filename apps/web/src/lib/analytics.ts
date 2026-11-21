// Shapes of index.json / GET /api/index and signals.json / GET /api/signals (docs/tasks/M4b.md).
// Hand-written until the API publishes them in OpenAPI; then switch to the generated types.
import { staticFirst } from './api'

export interface IndexPoint {
  month: string
  value: number | null
  n_products: number
  n_excluded: number
  provisional: boolean
}

export interface IndexCategory {
  code: number
  name: string
  points: IndexPoint[]
}

export interface IndexResponse {
  as_of: string
  base_month: string
  categories: IndexCategory[]
}

export type SignalType = 'jump' | 'outlier'

export interface Signal {
  type: SignalType
  barcode: string
  name: string
  retailer: string
  format: string
  date: string
  price_para: number
  reference_para: number
  ratio: number
}

export interface SignalsResponse {
  as_of: string
  items: Signal[]
}

export const fetchIndex = () => staticFirst<IndexResponse>('index.json', '/api/index')
export const fetchSignals = () => staticFirst<SignalsResponse>('signals.json', '/api/signals')

/** The newest point that has a value (provisional or final). */
export function latestPoint(category: IndexCategory): IndexPoint | undefined {
  return [...category.points].reverse().find((point) => point.value !== null)
}
