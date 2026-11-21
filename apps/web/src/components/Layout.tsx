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
  const link = 'text-brand underline underline-offset-2'
  return (
    <footer className="border-t border-line py-8 text-sm text-ink-soft">
      <p>{t('footerSources')}: <a href="https://data.gov.rs" className={link}>{t('source')}</a></p>
      <p className="mt-2">{t('footerLicense')}</p>
      <p className="mt-2"><a href={repoUrl} className={link}>{t('footerCode')}</a></p>
      <p className="mt-4 max-w-2xl">{t('disclaimer')}</p>
    </footer>
  )
}
