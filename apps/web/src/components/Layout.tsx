import { Link } from '@tanstack/react-router'
import { useI18n } from '../i18n/I18nProvider'

export interface StateViewProps {
  kind: 'loading' | 'empty' | 'error' | 'offline'
  title?: string
  message?: string
  onRetry?: () => void
  /** Number of skeleton blocks while loading; match the expected content to avoid layout shift. */
  lines?: number
}

export function StateView({ kind, title, message, onRetry, lines = 3 }: StateViewProps) {
  const { t } = useI18n()
  if (kind === 'loading') {
    return (
      <div role="status" aria-busy="true" className="flex flex-col gap-3">
        <span className="sr-only">{t('loading')}</span>
        {Array.from({ length: lines }, (_, index) => (
          <div key={index} aria-hidden="true" className="h-24 animate-pulse rounded-lg bg-paper-raised" />
        ))}
      </div>
    )
  }
  const heading = title ?? t(kind === 'empty' ? 'emptyTitle' : kind === 'offline' ? 'offlineTitle' : 'errorTitle')
  const body = message ?? (kind === 'empty' ? undefined : t('errorMessage'))
  return (
    <div role={kind === 'empty' ? 'status' : 'alert'} className="rounded-lg bg-paper-raised p-6">
      <p className="text-lg font-semibold">{heading}</p>
      {body && <p className="mt-2 text-ink-soft">{body}</p>}
      {onRetry && kind !== 'empty' && (
        <button type="button" onClick={onRetry}
          className="mt-4 min-h-11 rounded-md bg-brand px-5 font-semibold text-white hover:bg-brand-hover">
          {t('retry')}
        </button>
      )}
    </div>
  )
}

export function SiteFooter({ repoUrl = 'https://github.com/spasojewagner/korpa' }: { repoUrl?: string }) {
  const { t } = useI18n()
  const link = 'inline-flex min-h-11 items-center text-ink underline-offset-4 hover:underline'
  const heading = 'text-sm font-semibold uppercase tracking-wide text-ink-muted'
  return (
    <footer className="mt-16 bg-paper-raised text-ink-soft">
      <div aria-hidden="true" className="kilim kilim-lg" />
      <div className="wrap grid gap-10 py-12 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <img src="/logo.svg" alt={t('brand')} width={107} height={32} className="h-8 w-auto" />
          <p className="mt-2 max-w-sm">{t('footerTagline')}</p>
          <p className="mt-4 max-w-sm text-sm">{t('disclaimer')}</p>
        </div>
        <nav aria-label={t('footerShop')}>
          <p className={heading}>{t('footerShop')}</p>
          <ul className="mt-2">
            <li><Link to="/pretraga" className={link}>{t('navSearch')}</Link></li>
            <li><Link to="/korpa" className={link}>{t('navBasket')}</Link></li>
          </ul>
        </nav>
        <nav aria-label={t('footerData')}>
          <p className={heading}>{t('footerData')}</p>
          <ul className="mt-2">
            <li><Link to="/podaci/indeks" className={link}>{t('dataIndex')}</Link></li>
            <li><Link to="/podaci/kvalitet" className={link}>{t('navQuality')}</Link></li>
            <li><Link to="/podaci/api" className={link}>{t('dataApi')}</Link></li>
          </ul>
        </nav>
        <nav aria-label={t('footerProject')}>
          <p className={heading}>{t('footerProject')}</p>
          <ul className="mt-2">
            <li><Link to="/o-projektu" className={link}>{t('navAbout')}</Link></li>
            <li><a href={repoUrl} className={link}>{t('footerCode')}</a></li>
            <li><a href="https://data.gov.rs" className={link}>{t('source')}</a></li>
          </ul>
        </nav>
      </div>
      <div className="wrap border-t border-line py-6 text-sm">
        <p>{t('footerLicense')}</p>
      </div>
    </footer>
  )
}
