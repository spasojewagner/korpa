import { useId, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useI18n, type Script } from '../i18n/I18nProvider'
import { copy } from '../i18n/sr-Latn'
import { Icon } from './Icon'

const field = 'min-h-11 rounded-md border border-ink-muted bg-white px-3 text-base'
const primary = 'min-h-11 rounded-md bg-brand px-5 font-semibold text-white hover:bg-brand-hover'
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
      <div className="flex gap-2">
        <input id={id} name="q" type="search" required minLength={2} maxLength={100} autoComplete="off"
          defaultValue={defaultValue} placeholder={t('searchPlaceholder')}
          className={`${field} min-w-0 flex-1 placeholder:text-ink-muted`} />
        <button type="submit" className={primary}>{t('searchButton')}</button>
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
export function ScriptToggle() {
  const { script, setScript, t } = useI18n()
  const options: { value: Script; label: string }[] = [
    { value: 'latn', label: copy.latin },
    { value: 'cyrl', label: copy.cyrillic },
  ]
  return (
    <fieldset className="flex gap-4">
      <legend className="sr-only">{t('scriptLabel')}</legend>
      {options.map(({ value, label }) => (
        <label key={value} className="flex min-h-11 cursor-pointer items-center gap-2">
          <input type="radio" name="script" value={value} className="size-5 accent-brand"
            checked={script === value} onChange={() => setScript(value)} />
          <span lang={value === 'cyrl' ? 'sr-Cyrl' : 'sr-Latn'}>{label}</span>
        </label>
      ))}
    </fieldset>
  )
}
