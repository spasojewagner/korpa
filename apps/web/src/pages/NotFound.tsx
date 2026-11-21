import { Link } from '@tanstack/react-router'
import { useI18n } from '../i18n/I18nProvider'
import { usePageMeta } from '../lib/meta'

export function NotFound() {
  const { t } = useI18n()
  usePageMeta(t('notFoundHeading'))
  return (
    <>
      <h1 className="text-2xl font-semibold">{t('notFoundHeading')}</h1>
      <p className="mt-4 text-ink-soft">{t('notFoundText')}</p>
      <Link to="/" className="mt-4 inline-block text-brand underline underline-offset-2">{t('goHome')}</Link>
    </>
  )
}
