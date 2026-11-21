import { useEffect } from 'react'
import { useI18n } from '../i18n/I18nProvider'

/** Sets the document title and meta description for the current page. */
export function usePageMeta(title?: string) {
  const { t } = useI18n()
  const brand = t('brand')
  const description = t('metaDescription')
  useEffect(() => {
    document.title = title ? `${title} · ${brand}` : brand
    document.querySelector('meta[name="description"]')?.setAttribute('content', description)
  }, [title, brand, description])
}
