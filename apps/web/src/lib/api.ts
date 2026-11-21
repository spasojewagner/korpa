import type { components } from '../api/rest'
import type { TypedDocumentString } from '../gql/graphql'

export type Schemas = components['schemas']

const base = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

/** status 0 = network failure (offline or API unreachable). */
export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(base + path, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}) },
    })
  } catch {
    throw new ApiError(0, 'network')
  }
  if (!response.ok) throw new ApiError(response.status, response.statusText)
  return (await response.json()) as T
}

export const PAGE_SIZE = 20

export function searchProducts(q: string, category: number | undefined, offset: number) {
  const params = new URLSearchParams({ q, limit: String(PAGE_SIZE), offset: String(offset) })
  if (category) params.set('category', String(category))
  return request<Schemas['SearchResponse']>(`/api/search?${params}`)
}

export function compareBasket(items: Schemas['BasketItem'][]) {
  return request<Schemas['BasketResponse']>('/api/basket', { method: 'POST', body: JSON.stringify({ items }) })
}

/** Nightly static JSON first (served with the site), the API as fallback. */
async function staticFirst<T>(file: string, path: string): Promise<T> {
  try {
    const response = await fetch(`/data/${file}`)
    if (response.ok && response.headers.get('content-type')?.includes('json')) return (await response.json()) as T
  } catch {
    // Fall through to the API.
  }
  return request<T>(path)
}

export const fetchCategories = () => staticFirst<Schemas['CategoryItem'][]>('categories.json', '/api/categories')
export const fetchQuality = () => staticFirst<Schemas['QualityResponse']>('quality.json', '/api/quality')

export async function graphql<TResult, TVariables>(
  document: TypedDocumentString<TResult, TVariables>,
  variables: TVariables,
): Promise<TResult> {
  const body = await request<{ data?: TResult; errors?: { message: string }[] }>('/graphql', {
    method: 'POST',
    body: JSON.stringify({ query: document.toString(), variables }),
  })
  if (!body.data || body.errors?.length) throw new ApiError(200, body.errors?.[0]?.message ?? 'graphql')
  return body.data
}
