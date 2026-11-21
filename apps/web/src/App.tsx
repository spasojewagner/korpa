import { ScriptToggle, SiteFooter } from './components'
import { useI18n } from './i18n/I18nProvider'

export function App() {
  const { t } = useI18n()
  return <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6">
    <a className="skip-link" href="#main">{t('skip')}</a>
    <header className="flex flex-wrap items-center justify-between gap-6 border-b border-line py-6">
      <span className="text-2xl font-semibold">{t('brand')}</span>
      <ScriptToggle />
    </header>
    <main id="main" tabIndex={-1} className="flex-1 py-20">
      <p className="mb-4 font-semibold text-brand">{t('eyebrow')}</p>
      <h1 className="max-w-2xl text-3xl font-semibold">{t('title')}</h1>
      <p className="my-6 max-w-2xl text-lg text-ink-soft">{t('intro')}</p>
      <section className="mt-12 max-w-2xl rounded-lg bg-paper-raised p-6">
        <h2 className="text-xl font-semibold">{t('status')}</h2>
        <p className="mt-3 text-ink-soft">{t('explanation')}</p>
      </section>
    </main>
    <SiteFooter />
  </div>
}
