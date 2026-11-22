import { createLazyRoute } from '@tanstack/react-router'
import { useI18n } from '../i18n/I18nProvider'
import { aboutCopy } from '../i18n/about'
import { usePageMeta } from '../lib/meta'

type AboutKey = keyof typeof aboutCopy

const sections: [AboutKey, AboutKey][] = [
  ['aboutNotHeading', 'aboutNot'],
  ['aboutSourceHeading', 'aboutSource'],
  ['aboutMethodHeading', 'aboutMethod'],
]

function AboutPage() {
  const { t, tr } = useI18n()
  const a = (key: AboutKey) => tr(aboutCopy[key])
  usePageMeta(a('aboutHeading'))
  return (
    <article className="flex max-w-3xl flex-col gap-6">
      <h1 className="text-2xl font-semibold">{a('aboutHeading')}</h1>
      <p className="text-lg text-ink-soft">{a('aboutWhat')}</p>
      {sections.map(([heading, body]) => (
        <section key={heading}>
          <h2 className="text-xl font-semibold">{a(heading)}</h2>
          <p className="mt-2 text-ink-soft">{a(body)}</p>
        </section>
      ))}
      <section>
        <h2 className="text-xl font-semibold">{a('aboutContactHeading')}</h2>
        <p className="mt-2 text-ink-soft">
          {a('aboutContact')}{' '}
          <a href="https://github.com/spasojewagner/korpa/issues" className="text-brand underline underline-offset-2">{a('reportIssue')}</a>
        </p>
      </section>
      <p className="text-sm text-ink-muted">{t('disclaimer')}</p>
    </article>
  )
}

export const AboutRoute = createLazyRoute('/o-projektu')({ component: AboutPage })
