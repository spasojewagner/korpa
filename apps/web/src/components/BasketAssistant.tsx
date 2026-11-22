import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { assistantExamples } from '../i18n/assistant'
import { useI18n } from '../i18n/I18nProvider'
import { AssistantError, assistantErrorMessage, assistantStatus, assistantText, mergeBasketItems, selectedTotal, suggestBasket } from '../lib/ai-basket'
import type { Schemas } from '../lib/api'
import { basket, MAX_ITEMS, useBasket } from '../lib/basket'
import { formatDate, formatPrice } from '../lib/format'
import { QuantityStepper } from './Controls'
import { Icon } from './Icon'

type Proposal = Schemas['AiBasketItem'] & { selected: string }

export function BasketAssistant() {
  const status = useQuery({
    queryKey: ['ai-status'], queryFn: assistantStatus, staleTime: Infinity, gcTime: Infinity,
    retry: false, retryOnMount: false, refetchOnMount: false, refetchOnWindowFocus: false, refetchOnReconnect: false,
  })
  return status.isSuccess && status.data.enabled ? <AssistantForm /> : null
}

function Budget({ budget, total }: { budget: number | null; total: number }) {
  const i18n = useI18n()
  const a = assistantText(i18n)
  const over = budget !== null && total > budget
  return (
    <div className="rounded-lg bg-white p-5 shadow-card">
      <dl className="grid gap-4 sm:grid-cols-2">
        {budget !== null && (
          <div className="flex flex-col-reverse">
            <dt className="text-sm text-ink-muted">{a('assistantBudget')}</dt>
            <dd className="font-display text-2xl font-semibold tabular-nums">{formatPrice(budget)}</dd>
          </div>
        )}
        <div className="flex flex-col-reverse">
          <dt className="text-sm text-ink-muted">{a('assistantLowest')}</dt>
          <dd className="font-display text-2xl font-semibold tabular-nums">{formatPrice(total)}</dd>
        </div>
      </dl>
      {budget !== null && (
        <p className={`mt-3 flex items-center gap-2 font-semibold ${over ? 'text-danger' : 'text-brand'}`}>
          <Icon name={over ? 'alert' : 'check'} className="size-5" />
          {over ? a('assistantOver', { amount: formatPrice(total - budget) }) : a('assistantWithin')}
        </p>
      )}
      <p className="mt-2 text-sm text-ink-soft">{a('assistantLowestNote')}</p>
    </div>
  )
}

function AssistantForm() {
  const i18n = useI18n()
  const { t, tr } = i18n
  const a = assistantText(i18n)
  const id = useId()
  const field = useRef<HTMLTextAreaElement>(null)
  const section = useRef<HTMLElement>(null)
  const current = useBasket()
  const [sentence, setSentence] = useState('')
  const [proposals, setProposals] = useState<Proposal[]>([])
  const [budget, setBudget] = useState<number | null>(null)
  const [message, setMessage] = useState<'assistantReady' | 'assistantFull' | 'assistantAdded' | 'empty' | ''>('')
  const [added, setAdded] = useState(false)

  // "Isprobaj AI korpu" links here with #pomocnik; the form appears only after the status check.
  useEffect(() => {
    if (window.location.hash !== '#pomocnik') return
    section.current?.scrollIntoView({ block: 'start' })
    field.current?.focus({ preventScroll: true })
  }, [])

  const mutation = useMutation({
    mutationFn: suggestBasket, retry: false,
    onSuccess: (response) => {
      setProposals(response.items.map((item) => ({ ...item, candidates: item.candidates.slice(0, 5), selected: item.candidates[0]?.barcode ?? '' })))
      setBudget(response.budget_para ?? null)
      setMessage(response.items.length ? 'assistantReady' : 'empty')
    },
  })
  const fieldError = mutation.error instanceof AssistantError && mutation.error.status === 422
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setProposals([])
    setBudget(null)
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
  const goal = proposals.some((item) => item.proposed)
  const chip = 'inline-flex min-h-11 items-center rounded-full border border-ink-muted bg-white px-4 text-sm text-ink hover:border-ink hover:bg-paper'

  return (
    <section id="pomocnik" ref={section} aria-labelledby={`${id}-title`}
      className="my-8 scroll-mt-6 overflow-hidden rounded-xl border border-line bg-paper-raised">
      <div aria-hidden="true" className="kilim" />
      <div className="p-5 sm:p-8">
        <form onSubmit={submit} aria-busy={mutation.isPending} className="flex flex-col gap-4">
          <div>
            <h2 id={`${id}-title`} className="flex items-center gap-3 font-display text-2xl font-semibold sm:text-3xl">
              <span aria-hidden="true" className="grid size-10 place-items-center rounded-full bg-brand text-paper">
                <Icon name="sparkles" className="size-5" />
              </span>
              <label htmlFor={id}>{a('assistantLabel')}</label>
            </h2>
            <p className="mt-2 max-w-2xl text-ink-soft">{a('assistantIntro')}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-ink-muted">{a('assistantExamples')}</span>
            {assistantExamples.map((example) => (
              <button key={example} type="button" className={chip} onClick={() => { setSentence(tr(example)); field.current?.focus() }}>
                {tr(example)}
              </button>
            ))}
          </div>
          <textarea id={id} ref={field} value={sentence} onChange={(event) => setSentence(event.target.value)}
            required minLength={3} maxLength={300} rows={3} placeholder={a('assistantPlaceholder')}
            aria-invalid={fieldError || undefined} aria-describedby={`${id}-count ${id}-note${fieldError ? ` ${id}-error` : ''}`}
            className="w-full rounded-lg border-2 border-ink-muted bg-white p-4 text-lg placeholder:text-ink-muted focus:border-brand" />
          <p id={`${id}-count`} className="-mt-2 self-end text-sm tabular-nums text-ink-muted" aria-live="polite">{a('assistantCounter', { count: sentence.length })}</p>
          {fieldError && <p id={`${id}-error`} className="text-danger">{assistantErrorMessage(mutation.error, a)}</p>}
          <div className="flex flex-wrap items-center gap-4">
            <button type="submit" disabled={mutation.isPending} className="btn btn-primary disabled:opacity-60">
              <Icon name="sparkles" className="size-5" />
              {mutation.isPending ? t('loading') : a('assistantSubmit')}
            </button>
            <p id={`${id}-note`} className="max-w-md text-sm text-ink-soft">{a('assistantNote')}</p>
          </div>
        </form>
        <div role="status" aria-live="polite" aria-atomic="true" className="mt-4 text-ink-soft">
          {mutation.isError ? assistantErrorMessage(mutation.error, a)
            : message === 'empty' ? t('emptyTitle') : message ? a(message, { max: MAX_ITEMS }) : ''}
        </div>
        {proposals.length > 0 && (
          <div className="mt-6 flex flex-col gap-5">
            <h3 className="font-display text-2xl font-semibold">{a('assistantResults')}</h3>
            {goal && <p className="rounded-lg bg-brand-subtle p-4 text-ink">{a('assistantProposalNote')}</p>}
            <Budget budget={budget} total={selectedTotal(proposals)} />
            <ul className="grid gap-4 lg:grid-cols-2">
              {proposals.map((item, index) => (
                <li key={index} className="rounded-lg border border-line bg-paper p-4">
                  <fieldset disabled={added}>
                    <legend className="mb-3 flex flex-wrap items-center gap-2 font-semibold">
                      {item.phrase}
                      {item.proposed && (
                        <span className="rounded-full bg-paprika-subtle px-2.5 py-0.5 text-sm font-semibold text-paprika">{a('assistantProposed')}</span>
                      )}
                    </legend>
                    <QuantityStepper name={item.phrase} value={item.qty} onChange={(qty) => update(index, { qty })} />
                    <div className="mt-3 flex flex-col gap-2">
                      {item.candidates.map((candidate) => (
                        <label key={candidate.barcode}
                          className="flex min-h-11 cursor-pointer items-start gap-3 rounded-md border border-line bg-white p-3 has-[:checked]:border-brand has-[:checked]:bg-brand-subtle">
                          <input type="radio" name={`${id}-${index}`} value={candidate.barcode} checked={item.selected === candidate.barcode}
                            onChange={() => update(index, { selected: candidate.barcode })} className="mt-1 size-5 shrink-0 accent-brand" />
                          <span className="flex-1">
                            <span className="block font-semibold">{candidate.name}</span>
                            <span className="block text-sm text-ink-soft">{candidate.brand}</span>
                            <span className="mt-1 flex flex-wrap justify-between gap-x-3">
                              <span className="font-semibold tabular-nums">{t('priceFrom', { price: formatPrice(candidate.min_effective_para) })}</span>
                              <span className="text-sm text-ink-muted">{t('sourceDate', { date: formatDate(candidate.list_date) })}</span>
                            </span>
                          </span>
                        </label>
                      ))}
                    </div>
                    {item.candidates.length === 0 && <p className="mt-3">{a('assistantMissing')}.{' '}
                      <Link to="/pretraga" search={{ q: item.query }} className="text-brand underline">{t('goToSearch')}</Link>
                    </p>}
                    <label className="mt-2 flex min-h-11 cursor-pointer items-center gap-3 px-3">
                      <input type="radio" name={`${id}-${index}`} value="" checked={!item.selected}
                        onChange={() => update(index, { selected: '' })} className="size-5 accent-brand" />
                      {a('assistantSkip')}
                    </label>
                  </fieldset>
                </li>
              ))}
            </ul>
            <div>
              <button type="button" className="btn btn-primary disabled:opacity-60" onClick={add} disabled={added || !proposals.some((item) => item.selected)}>
                <Icon name="basket" className="size-5" />
                {a('assistantAdd')}
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
