import { Link, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import { useEffect, useRef } from 'react'
import { ScriptToggle, SearchForm, SiteFooter } from './components'
import { useI18n } from './i18n/I18nProvider'
import { useBasket } from './lib/basket'

const navLink = 'inline-flex min-h-11 items-center text-ink underline-offset-4 hover:underline'
const activeNav = { className: 'font-semibold underline', 'aria-current': 'page' as const }

export function RootLayout() {
  const { t, tp } = useI18n()
  const items = useBasket()
  const navigate = useNavigate()
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

  const count = tp('basketItems', items.length)
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 sm:px-6">
      <a className="skip-link" href="#main">{t('skip')}</a>
      <header className="flex flex-col gap-4 border-b border-line py-4">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
          <Link to="/" className="inline-flex min-h-11 items-center text-2xl font-semibold text-ink">{t('brand')}</Link>
          <nav aria-label={t('navLabel')}>
            <ul className="flex flex-wrap items-center gap-x-5">
              <li>
                <Link to="/korpa" className={navLink} activeProps={activeNav}>
                  <span className="sr-only">{`${t('navBasket')}: ${count}`}</span>
                  <span aria-hidden="true">
                    {t('navBasket')}
                    <span className="ml-2 rounded-sm bg-brand px-2 text-sm font-semibold text-white tabular-nums">{items.length}</span>
                  </span>
                </Link>
              </li>
              <li><Link to="/indeks" className={navLink} activeProps={activeNav}>{t('navIndex')}</Link></li>
              <li><Link to="/kvalitet" className={navLink} activeProps={activeNav}>{t('navQuality')}</Link></li>
              <li><Link to="/o-projektu" className={navLink} activeProps={activeNav}>{t('navAbout')}</Link></li>
            </ul>
          </nav>
          <ScriptToggle />
        </div>
        {pathname !== '/' && (
          <div className="max-w-2xl">
            <SearchForm key={q} defaultValue={q} onSearch={(query) => navigate({ to: '/pretraga', search: { q: query } })} />
          </div>
        )}
        <p aria-live="polite" className="sr-only">{t('basketLive', { items: count })}</p>
      </header>
      <main id="main" tabIndex={-1} className="flex-1 py-8 focus:outline-none">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  )
}
