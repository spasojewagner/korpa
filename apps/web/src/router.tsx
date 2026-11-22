import { createRootRoute, createRoute, createRouter, redirect } from '@tanstack/react-router'
import { RootLayout } from './Layout'
import { NotFound } from './pages/NotFound'

export interface SearchQuery {
  q?: string
  kategorija?: number
}

/** URL search params are untrusted: keep only a bounded query and a category code 1–25. */
export function parseSearch(search: Record<string, unknown>): SearchQuery {
  const raw = typeof search.q === 'string' ? search.q : typeof search.q === 'number' ? String(search.q) : ''
  const q = raw.trim().slice(0, 100)
  const category = Number(search.kategorija)
  return {
    q: q || undefined,
    kategorija: Number.isInteger(category) && category >= 1 && category <= 25 ? category : undefined,
  }
}

const rootRoute = createRootRoute({ component: RootLayout, notFoundComponent: NotFound })

// Every page is its own chunk; Home stays small because only data pages pull in TanStack Query.
const home = createRoute({ getParentRoute: () => rootRoute, path: '/' })
  .lazy(() => import('./pages/Home').then((m) => m.Route))
const search = createRoute({ getParentRoute: () => rootRoute, path: '/pretraga', validateSearch: parseSearch })
  .lazy(() => import('./pages/Search').then((m) => m.Route))
const product = createRoute({ getParentRoute: () => rootRoute, path: '/proizvod/$barcode' })
  .lazy(() => import('./pages/Product').then((m) => m.Route))
const basketPage = createRoute({ getParentRoute: () => rootRoute, path: '/korpa' })
  .lazy(() => import('./pages/Basket').then((m) => m.Route))
const about = createRoute({ getParentRoute: () => rootRoute, path: '/o-projektu' })
  .lazy(() => import('./pages/Static').then((m) => m.AboutRoute))

// Data area (index, signals, quality, API) for journalists, researchers and developers.
const data = createRoute({ getParentRoute: () => rootRoute, path: '/podaci' })
  .lazy(() => import('./pages/Data').then((m) => m.OverviewRoute))
const index = createRoute({ getParentRoute: () => rootRoute, path: '/podaci/indeks' })
  .lazy(() => import('./pages/PriceIndex').then((m) => m.Route))
const quality = createRoute({ getParentRoute: () => rootRoute, path: '/podaci/kvalitet' })
  .lazy(() => import('./pages/Quality').then((m) => m.Route))
const api = createRoute({ getParentRoute: () => rootRoute, path: '/podaci/api' })
  .lazy(() => import('./pages/Data').then((m) => m.ApiRoute))

// Old addresses keep working.
const oldIndex = createRoute({
  getParentRoute: () => rootRoute, path: '/indeks',
  beforeLoad: () => { throw redirect({ to: '/podaci/indeks', replace: true }) },
})
const oldQuality = createRoute({
  getParentRoute: () => rootRoute, path: '/kvalitet',
  beforeLoad: () => { throw redirect({ to: '/podaci/kvalitet', replace: true }) },
})

export const router = createRouter({
  routeTree: rootRoute.addChildren([
    home, search, product, basketPage, about, data, index, quality, api, oldIndex, oldQuality,
  ]),
  defaultPreload: 'intent',
  scrollRestoration: true,
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
