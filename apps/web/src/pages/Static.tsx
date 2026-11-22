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
    <article className="flex max-w-3xl flex-col gap-8">
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">{a('aboutHeading')}</h1>
      <p className="text-lg text-ink-soft">{a('aboutWhat')}</p>
      {sections.map(([heading, body]) => (
        <section key={heading} className="border-t border-line pt-8">
          <h2 className="font-display text-2xl">{a(heading)}</h2>
          <p className="mt-2 text-ink-soft">{a(body)}</p>
        </section>
      ))}
      <section className="border-t border-line pt-8">
        <h2 className="font-display text-2xl">{a('aboutContactHeading')}</h2>
        <p className="mt-2 text-ink-soft">
          {a('aboutContact')}{' '}
          <a href="https://github.com/spasojewagner/korpa/issues" className="text-brand underline underline-offset-2">{a('reportIssue')}</a>
        </p>
      </section>
      <p className="border-t border-line pt-8 text-sm text-ink-muted">{t('disclaimer')}</p>
    </article>
  )
}

export const AboutRoute = createLazyRoute('/o-projektu')({ component: AboutPage })
