import { useEffect, useState } from 'react'
import { copy } from './i18n/sr-Latn'
import { transliterate } from './i18n/transliterate'

export function App() {
  const [cyrillic, setCyrillic] = useState(() => localStorage.getItem('script') === 'cyrl')
  const t = (key: keyof typeof copy) => cyrillic ? transliterate(copy[key]) : copy[key]
  useEffect(() => {
    document.documentElement.lang = cyrillic ? 'sr-Cyrl' : 'sr-Latn'
    localStorage.setItem('script', cyrillic ? 'cyrl' : 'latn')
  }, [cyrillic])
  return <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6">
    <a className="skip-link" href="#main">{t('skip')}</a>
    <header className="flex flex-wrap items-center justify-between gap-6 border-b border-line py-6">
      <span className="text-2xl font-semibold">{t('brand')}</span>
      <fieldset className="flex gap-4">
        <legend className="sr-only">{t('scriptLabel')}</legend>
        {(['latn', 'cyrl'] as const).map(value => <label className="flex min-h-11 items-center gap-2" key={value}>
          <input className="size-5 accent-brand" type="radio" name="script" value={value}
            checked={cyrillic === (value === 'cyrl')}
            onChange={() => setCyrillic(value === 'cyrl')} />
          {copy[value === 'latn' ? 'latin' : 'cyrillic']}
        </label>)}
      </fieldset>
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
    <footer className="border-t border-line py-8 text-sm text-ink-soft">
      <a href="https://data.gov.rs" className="text-brand underline">{t('source')}</a>
      <p className="mt-3 max-w-2xl">{t('disclaimer')}</p>
    </footer>
  </div>
}
