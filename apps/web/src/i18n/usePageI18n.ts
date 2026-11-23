import { useI18n } from './I18nProvider'
import { pageCopy, type PageCopyKey } from './pages'
import type { CopyKey } from './sr-Latn'

export type PageKey = CopyKey | PageCopyKey

/** Page copy stays in lazy chunks; placeholders are filled after transliteration. */
export function usePageI18n() {
  const shared = useI18n()
  return {
    ...shared,
    t: (key: PageKey, vars: Record<string, string | number> = {}) => {
      if (!(key in pageCopy)) return shared.t(key as CopyKey, vars)
      return shared.tr(pageCopy[key as PageCopyKey]).replace(/\{(\w+)\}/g,
        (match, name: string) => name in vars ? String(vars[name]) : match)
    },
  }
}
