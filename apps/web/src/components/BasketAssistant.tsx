import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useId, useState, type FormEvent } from 'react'
import { useI18n } from '../i18n/I18nProvider'
import { AssistantError, assistantErrorMessage, assistantStatus, assistantText, mergeBasketItems, suggestBasket } from '../lib/ai-basket'
import type { Schemas } from '../lib/api'
import { basket, MAX_ITEMS, useBasket } from '../lib/basket'
import { formatDate, formatPrice } from '../lib/format'
import { QuantityStepper } from './Controls'

type Proposal = Schemas['AiBasketItem'] & { selected: string }
const primary = 'min-h-11 rounded-md bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-hover disabled:opacity-50'

export function BasketAssistant() {
  const status = useQuery({
    queryKey: ['ai-status'], queryFn: assistantStatus, staleTime: Infinity, gcTime: Infinity,
    retry: false, retryOnMount: false, refetchOnMount: false, refetchOnWindowFocus: false, refetchOnReconnect: false,
  })
  return status.isSuccess && status.data.enabled ? <AssistantForm /> : null
}

function AssistantForm() {
  const i18n = useI18n()
  const { t } = i18n
  const a = assistantText(i18n)
  const id = useId()
  const current = useBasket()
  const [sentence, setSentence] = useState('')
  const [proposals, setProposals] = useState<Proposal[]>([])
  const [message, setMessage] = useState<'assistantReady' | 'assistantFull' | 'assistantAdded' | 'empty' | ''>('')
  const [added, setAdded] = useState(false)
  const mutation = useMutation({
    mutationFn: suggestBasket, retry: false,
    onSuccess: (response) => {
      setProposals(response.items.map((item) => ({ ...item, candidates: item.candidates.slice(0, 5), selected: item.candidates[0]?.barcode ?? '' })))
      setMessage(response.items.length ? 'assistantReady' : 'empty')
    },
  })
  const fieldError = mutation.error instanceof AssistantError && mutation.error.status === 422
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setProposals([])
    setMessage('')
    setAdded(false)
    mutation.mutate(sentence.trim())
  }
  const update = (index: number, patch: Partial<Proposal>) => {
    setProposals((items) => items.map((item, i) => i === index ? { ...item, ...patch } : item))
    setMessage('')
  }
  const add = () => {
    const chosen = proposals.filter((item) => item.selected).map((item) => ({ barcode: item.selected, qty: item.qty }))
    const merged = mergeBasketItems(current, chosen)
    if (!merged) {
      setMessage('assistantFull')
      return
    }
    for (const item of merged) {
      if (current.some((existing) => existing.barcode === item.barcode && existing.qty === item.qty)) continue
      basket.add(item.barcode)
      basket.setQty(item.barcode, item.qty)
    }
    setAdded(true)
    setMessage('assistantAdded')
  }

  return (
    <section className="my-6 rounded-lg border border-line bg-paper-raised p-4 sm:p-6" aria-label={a('assistantLabel')}>
      <form onSubmit={submit} aria-busy={mutation.isPending} className="flex flex-col items-start gap-3">
        <label htmlFor={id} className="text-xl font-semibold">{a('assistantLabel')}</label>
        <textarea id={id} value={sentence} onChange={(event) => setSentence(event.target.value)}
          required minLength={3} maxLength={300} rows={3} placeholder={a('assistantPlaceholder')}
          aria-invalid={fieldError || undefined} aria-describedby={`${id}-count ${id}-note${fieldError ? ` ${id}-error` : ''}`}
          className="w-full rounded-md border border-ink-muted bg-white p-3 placeholder:text-ink-muted" />
        <p id={`${id}-count`} className="self-end text-sm tabular-nums text-ink-muted" aria-live="polite">{a('assistantCounter', { count: sentence.length })}</p>
        {fieldError && <p id={`${id}-error`} className="text-danger">{assistantErrorMessage(mutation.error, a)}</p>}
        <button type="submit" disabled={mutation.isPending} className={primary}>
          {mutation.isPending ? t('loading') : a('assistantSubmit')}
        </button>
        <p id={`${id}-note`} className="text-sm text-ink-soft">{a('assistantNote')}</p>
      </form>
      <div role="status" aria-live="polite" aria-atomic="true" className="mt-3 text-ink-soft">
        {mutation.isError ? assistantErrorMessage(mutation.error, a)
          : message === 'empty' ? t('emptyTitle') : message ? a(message, { max: MAX_ITEMS }) : ''}
      </div>
      {proposals.length > 0 && (
        <div className="mt-5">
          <h2 className="text-xl font-semibold">{a('assistantResults')}</h2>
          <ul className="my-4 flex flex-col gap-4">
            {proposals.map((item, index) => (
              <li key={index} className="rounded-md border border-line bg-paper p-4">
                <fieldset disabled={added}>
                  <legend className="mb-3 font-semibold">{item.phrase}</legend>
                  <QuantityStepper name={item.phrase} value={item.qty} onChange={(qty) => update(index, { qty })} />
                  {item.candidates.map((candidate) => (
                    <label key={candidate.barcode} className="mt-2 flex min-h-11 cursor-pointer items-start gap-3 py-2">
                      <input type="radio" name={`${id}-${index}`} value={candidate.barcode} checked={item.selected === candidate.barcode}
                        onChange={() => update(index, { selected: candidate.barcode })} className="mt-1 size-5 shrink-0 accent-brand" />
                      <span>
                        <span className="block font-semibold">{candidate.name}</span>
                        <span className="block text-ink-soft">{candidate.brand}</span>
                        <span className="block tabular-nums">{t('priceFrom', { price: formatPrice(candidate.min_effective_para) })}</span>
                        <span className="block text-sm text-ink-muted">{t('sourceDate', { date: formatDate(candidate.list_date) })}</span>
                      </span>
                    </label>
                  ))}
                  {item.candidates.length === 0 && <p className="mt-3">{a('assistantMissing')}.{' '}
                    <Link to="/pretraga" search={{ q: item.query }} className="text-brand underline">{t('goToSearch')}</Link>
                  </p>}
                  <label className="flex min-h-11 cursor-pointer items-center gap-3">
                    <input type="radio" name={`${id}-${index}`} value="" checked={!item.selected}
                      onChange={() => update(index, { selected: '' })} className="size-5 accent-brand" />
                    {a('assistantSkip')}
                  </label>
                </fieldset>
              </li>
            ))}
          </ul>
          <button type="button" className={primary} onClick={add} disabled={added || !proposals.some((item) => item.selected)}>{a('assistantAdd')}</button>
        </div>
      )}
    </section>
  )
}
