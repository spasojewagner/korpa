import { createLazyRoute } from '@tanstack/react-router'
import { useI18n } from '../i18n/I18nProvider'
import type { CopyKey } from '../i18n/sr-Latn'
import { usePageMeta } from '../lib/meta'

const sections: [CopyKey, CopyKey][] = [
  ['aboutNotHeading', 'aboutNot'],
  ['aboutSourceHeading', 'aboutSource'],
  ['aboutMethodHeading', 'aboutMethod'],
]

function AboutPage() {
  const { t } = useI18n()
  usePageMeta(t('aboutHeading'))
  return (
    <article className="flex max-w-3xl flex-col gap-6">
      <h1 className="text-2xl font-semibold">{t('aboutHeading')}</h1>
      <p className="text-lg text-ink-soft">{t('aboutWhat')}</p>
      {sections.map(([heading, body]) => (
        <section key={heading}>
          <h2 className="text-xl font-semibold">{t(heading)}</h2>
          <p className="mt-2 text-ink-soft">{t(body)}</p>
        </section>
      ))}
      <section>
        <h2 className="text-xl font-semibold">{t('aboutContactHeading')}</h2>
        <p className="mt-2 text-ink-soft">
          {t('aboutContact')}{' '}
          <a href="https://github.com/spasojewagner/korpa/issues" className="text-brand underline underline-offset-2">{t('reportIssue')}</a>
        </p>
      </section>
      <p className="text-sm text-ink-muted">{t('disclaimer')}</p>
    </article>
  )
}

export const AboutRoute = createLazyRoute('/o-projektu')({ component: AboutPage })
