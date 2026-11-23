import { Link } from '@tanstack/react-router'
import { useI18n } from '../i18n/I18nProvider'
import { usePageMeta } from '../lib/meta'

export function NotFound() {
  const { t } = useI18n()
  usePageMeta(t('notFoundHeading'), t('notFoundText'))
  return (
    <article className="max-w-3xl rounded-lg bg-paper-raised p-6">
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">{t('notFoundHeading')}</h1>
      <p className="mt-4 text-lg text-ink-soft">{t('notFoundText')}</p>
      <div className="mt-6">
        <Link to="/" className="btn btn-primary">{t('goHome')}</Link>
      </div>
    </article>
  )
}
