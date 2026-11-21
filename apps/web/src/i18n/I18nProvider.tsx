import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { copy, plurals, type CopyKey, type PluralKey } from './sr-Latn'
import { transliterate } from './transliterate'

export type Script = 'latn' | 'cyrl'
type Vars = Record<string, string | number>

export interface I18n {
  script: Script
  setScript: (script: Script) => void
  /** UI copy in the current script. Vars are inserted after transliteration, so data stays as published. */
  t: (key: CopyKey, vars?: Vars) => string
  /** Plural copy; `n` is available as {n}. */
  tp: (key: PluralKey, n: number, vars?: Vars) => string
}

const rules = new Intl.PluralRules('sr-Latn')

function fill(template: string, vars: Vars = {}): string {
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match,
  )
}

function readScript(): Script {
  try {
    return localStorage.getItem('script') === 'cyrl' ? 'cyrl' : 'latn'
  } catch {
    return 'latn'
  }
}

export function createI18n(script: Script, setScript: (script: Script) => void = () => {}): I18n {
  // Placeholders like {date} are kept as is, so they can still be filled after transliteration.
  const inScript = (text: string) =>
    script === 'cyrl'
      ? text.split(/(\{\w+\})/).map((part) => (part.startsWith('{') ? part : transliterate(part))).join('')
      : text
  return {
    script,
    setScript,
    t: (key, vars) => fill(inScript(copy[key]), vars),
    tp: (key, n, vars) => {
      const forms: Record<string, string> = plurals[key]
      const form = forms[rules.select(n)] ?? forms.other
      return fill(inScript(form), { ...vars, n })
    },
  }
}

const I18nContext = createContext<I18n>(createI18n('latn'))

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Script }) {
  const [script, setScript] = useState<Script>(() => initial ?? readScript())
  useEffect(() => {
    document.documentElement.lang = script === 'cyrl' ? 'sr-Cyrl' : 'sr-Latn'
    try {
      localStorage.setItem('script', script)
    } catch {
      // Storage can be unavailable (private mode); the choice then lasts for this visit only.
    }
  }, [script])
  const value = useMemo(() => createI18n(script, setScript), [script])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18n {
  return useContext(I18nContext)
}
