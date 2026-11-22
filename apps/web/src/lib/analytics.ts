// Shapes of index.json / GET /api/index and signals.json / GET /api/signals (docs/tasks/M4b.md).
import { staticFirst, type Schemas } from './api'

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
  /** Only in the nightly index.json, and only when at least one sentence passed the number check. */
  notes?: { model: string; items: string[] }
}

export type SignalsResponse = Schemas['SignalsResponse']
export type Signal = SignalsResponse['items'][number]
export type SignalType = Signal['type']

export const fetchIndex = () => staticFirst<IndexResponse>('index.json', '/api/index')
export const fetchSignals = () => staticFirst<SignalsResponse>('signals.json', '/api/signals')

/** The newest point that has a value (provisional or final). */
export function latestPoint(category: IndexCategory): IndexPoint | undefined {
  return [...category.points].reverse().find((point) => point.value !== null)
}
