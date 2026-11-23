import { usePageI18n } from '../i18n/usePageI18n'

export interface StateViewProps {
  kind: 'loading' | 'empty' | 'error' | 'offline'
  title?: string
  message?: string
  onRetry?: () => void
  /** Number of skeleton blocks while loading; match the expected content to avoid layout shift. */
  lines?: number
}

export function StateView({ kind, title, message, onRetry, lines = 3 }: StateViewProps) {
  const { t } = usePageI18n()
  if (kind === 'loading') {
    return (
      <div role="status" aria-busy="true" className="flex flex-col gap-3 rounded-lg bg-paper-raised p-5">
        <p className="font-display text-2xl font-semibold">{t('loading')}</p>
        {Array.from({ length: lines }, (_, index) => (
          <div key={index} aria-hidden="true" className="h-24 animate-pulse rounded-md bg-sand" />
        ))}
      </div>
    )
  }
  const heading = title ?? t(kind === 'empty' ? 'emptyTitle' : kind === 'offline' ? 'offlineTitle' : 'errorTitle')
  const body = message ?? (kind === 'empty' ? undefined : t('errorMessage'))
  return (
    <div role={kind === 'empty' ? 'status' : 'alert'} className="rounded-lg bg-paper-raised p-6">
      <h2 className="font-display text-2xl font-semibold">{heading}</h2>
      {body && <p className="mt-2 text-ink-soft">{body}</p>}
      {onRetry ? (
        <button type="button" onClick={onRetry}
          className="btn btn-primary mt-4">
          {t('retry')}
        </button>
      ) : <a href="/" className="btn btn-primary mt-4">{t('goHome')}</a>}
    </div>
  )
}

