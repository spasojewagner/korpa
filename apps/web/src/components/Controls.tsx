import { useId, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useI18n, type Script } from '../i18n/I18nProvider'
import { copy } from '../i18n/sr-Latn'
import { Icon } from './Icon'

const square =
  'inline-flex size-11 items-center justify-center rounded-md border border-ink-muted bg-white text-ink ' +
  'hover:bg-paper-raised disabled:cursor-not-allowed disabled:opacity-50'

export interface SearchFormProps {
  defaultValue?: string
  /** Client-side navigation. Without it the form submits GET /pretraga?q= (works without JS). */
  onSearch?: (query: string) => void
}

export function SearchForm({ defaultValue = '', onSearch }: SearchFormProps) {
  const { t } = useI18n()
  const id = useId()
  const submit = (event: FormEvent<HTMLFormElement>) => {
    if (!onSearch) return
    event.preventDefault()
    const query = new FormData(event.currentTarget).get('q')
    const value = typeof query === 'string' ? query.trim() : ''
    if (value.length >= 2) onSearch(value)
  }
  return (
    <form role="search" action="/pretraga" method="get" onSubmit={submit} className="flex w-full flex-col gap-2">
      <label htmlFor={id} className="font-semibold">{t('searchLabel')}</label>
      <div className="flex items-center gap-2 rounded-full border-2 border-ink-muted bg-white p-1.5 pl-4 focus-within:outline-3 focus-within:outline-offset-2 focus-within:outline-focus">
        <Icon name="search" className="size-5 shrink-0 text-ink-muted" />
        <input id={id} name="q" type="search" required minLength={2} maxLength={100} autoComplete="off"
          defaultValue={defaultValue} placeholder={t('searchPlaceholder')}
          className="min-h-11 min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-ink-muted" />
        <button type="submit" className="btn btn-primary min-h-11 px-5">{t('searchButton')}</button>
      </div>
    </form>
  )
}

export interface QuantityStepperProps {
  value: number
  onChange: (value: number) => void
  /** Product name, used in the accessible labels ("Količina: Mleko 1 l"). */
  name: string
  min?: number
  max?: number
}

export function QuantityStepper({ value, onChange, name, min = 1, max = 99 }: QuantityStepperProps) {
  const { t } = useI18n()
  const id = useId()
  // null = show `value`; a string = the user is typing.
  const [draft, setDraft] = useState<string | null>(null)
  const commit = (next: number) => {
    const clamped = Math.min(max, Math.max(min, Number.isFinite(next) ? next : min))
    setDraft(null)
    if (clamped !== value) onChange(clamped)
  }
  const typed = () => commit(draft === null || draft === '' ? value : Number(draft))
  const keys = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') typed()
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      event.preventDefault()
      commit(value + (event.key === 'ArrowUp' ? 1 : -1))
    }
  }
  const label = `${t('quantity')}: ${name}`
  return (
    <div className="inline-flex items-center gap-1">
      <button type="button" className={square} disabled={value <= min} onClick={() => commit(value - 1)}
        aria-label={`${t('decrease')}: ${name}`}>
        <Icon name="minus" className="size-5" />
      </button>
      <label htmlFor={id} className="sr-only">{label}</label>
      <input id={id} inputMode="numeric" pattern="[0-9]*" autoComplete="off"
        value={draft ?? String(value)}
        onChange={(event) => setDraft(event.target.value.replace(/\D/g, '').slice(0, 2))}
        onBlur={typed} onKeyDown={keys}
        className="h-11 w-14 rounded-md border border-ink-muted bg-white text-center tabular-nums" />
      <button type="button" className={square} disabled={value >= max} onClick={() => commit(value + 1)}
        aria-label={`${t('increase')}: ${name}`}>
        <Icon name="plus" className="size-5" />
      </button>
    </div>
  )
}

/** Latinica / Ћирилица. Each option is always written in its own script. */
export function ScriptToggle({ tone = 'light' }: { tone?: 'light' | 'dark' }) {
  const { script, setScript, t } = useI18n()
  const options: { value: Script; label: string; short: string }[] = [
    { value: 'latn', label: copy.latin, short: copy.latinShort },
    { value: 'cyrl', label: copy.cyrillic, short: copy.cyrillicShort },
  ]
  const frame = tone === 'dark' ? 'border-sand/60' : 'border-ink-muted'
  const idle = tone === 'dark' ? 'text-paper hover:bg-brand' : 'text-ink hover:bg-paper-raised'
  const active = tone === 'dark' ? 'bg-paper text-brand-deep' : 'bg-ink text-paper'
  return (
    <fieldset className={`flex rounded-full border p-1 ${frame}`}>
      <legend className="sr-only">{t('scriptLabel')}</legend>
      {options.map(({ value, label, short }) => (
        <label key={value}
          className={`relative flex min-h-10 min-w-11 cursor-pointer items-center justify-center rounded-full px-3 text-sm font-semibold has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus ${script === value ? active : idle}`}>
          <input type="radio" name="script" value={value} className="absolute inset-0 m-0 cursor-pointer appearance-none rounded-full"
            checked={script === value} onChange={() => setScript(value)} />
          <span aria-hidden="true" lang={value === 'cyrl' ? 'sr-Cyrl' : 'sr-Latn'}>{short}</span>
          <span className="sr-only" lang={value === 'cyrl' ? 'sr-Cyrl' : 'sr-Latn'}>{label}</span>
        </label>
      ))}
    </fieldset>
  )
}
