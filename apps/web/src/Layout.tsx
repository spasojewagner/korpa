import { lazy, Suspense } from 'react'
import { Link, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import { useEffect, useRef } from 'react'
import { Icon, ScriptToggle, SearchForm, SiteFooter } from './components'
import { useI18n } from './i18n/I18nProvider'
import { useBasket } from './lib/basket'

const activeNav = { 'aria-current': 'page' as const, className: 'is-active' }

/** The logo is a static SVG (no JS cost); the dark variant sits on the Podaci band. */
export function Logo({ tone }: { tone: 'light' | 'dark' }) {
  const { t } = useI18n()
  return (
    <Link to="/" aria-label={t('homeLabel')} className="inline-flex min-h-11 items-center">
      <img src={tone === 'dark' ? '/logo-dark.svg' : '/logo.svg'} alt="" width={120} height={36} className="h-9 w-auto" />
    </Link>
  )
}

/** Shopper area: search, basket, product pages and the About page. */
function ShopHeader({ pathname, q }: { pathname: string; q: string }) {
  const { t, tp } = useI18n()
  const items = useBasket()
  const navigate = useNavigate()
  const count = tp('basketItems', items.length)
  const link = 'nav-link inline-flex min-h-11 items-center px-1 text-ink'
  return (
    <header>
      <div aria-hidden="true" className="kilim" />
      <div className="wrap grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 py-3 sm:grid-cols-[auto_1fr_auto_auto] sm:gap-x-6">
        <div className="order-1"><Logo tone="light" /></div>
        <nav aria-label={t('navLabel')} className="order-3 sm:order-2 sm:justify-self-center">
          <ul className="flex flex-wrap items-center gap-x-4 sm:gap-x-7">
            <li><Link to="/pretraga" className={link} activeProps={activeNav}>{t('navSearch')}</Link></li>
            <li><Link to="/podaci" className={link} activeProps={activeNav}>{t('navData')}</Link></li>
            <li className="hidden sm:list-item"><Link to="/o-projektu" className={link} activeProps={activeNav}>{t('navAbout')}</Link></li>
          </ul>
        </nav>
        <div className="order-4 justify-self-end sm:order-3"><ScriptToggle /></div>
        <Link to="/korpa" className="btn btn-primary order-2 min-h-11 px-4 sm:order-4" activeProps={{ 'aria-current': 'page' }}>
          <Icon name="basket" className="size-5" />
          <span className="sr-only">{`${t('navBasket')}: ${count}`}</span>
          <span aria-hidden="true" className="max-[359px]:hidden">{t('navBasket')}</span>
          <span aria-hidden="true" className="rounded-full bg-paper px-2 text-sm text-brand tabular-nums">{items.length}</span>
        </Link>
      </div>
      {pathname !== '/' && (
        <div className="wrap pb-4">
          <div className="max-w-2xl">
            <SearchForm key={q} defaultValue={q} onSearch={(query) => navigate({ to: '/pretraga', search: { q: query } })} />
          </div>
        </div>
      )}
      <p aria-live="polite" className="sr-only">{t('basketLive', { items: count })}</p>
    </header>
  )
}

/** Data area for journalists, researchers and developers: its own band and tabs. */
const DataHeader = lazy(() => import('./components/DataHeader'))

export function RootLayout() {
  const { t } = useI18n()
  const { pathname, q } = useRouterState({
    select: (state) => ({
      pathname: state.location.pathname,
      q: (state.location.search as { q?: string }).q ?? '',
    }),
  })

  // After client-side navigation, move focus to the new page so screen readers start there.
  const firstRender = useRef(true)
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    document.getElementById('main')?.focus()
  }, [pathname])

  const dataArea = pathname === '/podaci' || pathname.startsWith('/podaci/')
  const fullBleed = pathname === '/'
  return (
    <div className="flex min-h-screen flex-col">
      <a className="skip-link" href="#main">{t('skip')}</a>
      {dataArea ? <Suspense fallback={<div className="h-40 bg-brand-deep" />}><DataHeader /></Suspense> : <ShopHeader pathname={pathname} q={q} />}
      <main id="main" tabIndex={-1} className={`flex-1 focus:outline-none ${fullBleed ? '' : 'wrap py-10'}`}>
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  )
}
