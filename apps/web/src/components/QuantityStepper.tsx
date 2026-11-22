import { useId, useState, type KeyboardEvent } from 'react'
import { usePageI18n } from '../i18n/usePageI18n'
import { Icon } from './Icon'
const square =
  'inline-flex size-11 items-center justify-center rounded-md border border-ink-muted bg-white text-ink ' +
  'hover:bg-paper-raised disabled:cursor-not-allowed disabled:opacity-50'

export interface QuantityStepperProps {
  value: number
  onChange: (value: number) => void
  /** Product name, used in the accessible labels ("Količina: Mleko 1 l"). */
  name: string
  min?: number
  max?: number
}

export function QuantityStepper({ value, onChange, name, min = 1, max = 99 }: QuantityStepperProps) {
  const { t } = usePageI18n()
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

