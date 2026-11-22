import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link, createLazyRoute } from '@tanstack/react-router'
import { BasketSummary, QuantityStepper, StateView, type BasketTotal } from '../components'
import { ProductsSummaryDocument } from '../gql/graphql'
import { useI18n } from '../i18n/I18nProvider'
import { ApiError, compareBasket, graphql, type Schemas } from '../lib/api'
import { basket, useBasket } from '../lib/basket'
import { usePageMeta } from '../lib/meta'
import { WithQuery } from '../lib/query'
import { BasketAssistant } from '../components/BasketAssistant'
import { BasketSplit } from '../components/BasketSplit'

export function toTotals(response: Schemas['BasketResponse']): BasketTotal[] {
  return response.retailers.flatMap((retailer) => retailer.formats.map((format) => ({
    key: String(format.id),
    retailer: retailer.name,
    format: format.name,
    totalPara: format.total_para,
    complete: format.complete,
    missing: format.missing_barcodes.length,
    listDate: format.list_date_min ?? response.as_of,
  })))
}

function BasketPage() {
  const { t } = useI18n()
  const items = useBasket()
  const barcodes = items.map((item) => item.barcode)
  usePageMeta(t('basketHeading'))

  const names = useQuery({
    queryKey: ['names', barcodes],
    queryFn: () => graphql(ProductsSummaryDocument, { barcodes }),
    enabled: barcodes.length > 0,
    placeholderData: keepPreviousData,
  })
  const totals = useQuery({
    queryKey: ['basket', items],
    queryFn: () => compareBasket(items),
    enabled: items.length > 0,
    placeholderData: keepPreviousData,
  })
  const byBarcode = new Map((names.data?.products ?? []).flatMap((product) => (product ? [[product.barcode, product]] : [])))

  return (
    <>
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">{t('basketHeading')}</h1>
      <BasketAssistant />
      {items.length === 0 ? (
        <div className="mt-6 flex flex-col items-start gap-4 rounded-lg bg-paper-raised p-5">
          <p className="font-display text-2xl">{t('basketEmpty')}</p>
          <Link to="/pretraga" className="btn btn-primary">{t('goToSearch')}</Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-10 lg:grid-cols-2">
          <section aria-labelledby="items">
            <h2 id="items" className="mb-5 font-display text-2xl">{t('basketItemsHeading')}</h2>
            <ul className="flex flex-col gap-4">
              {items.map((item) => {
                const product = byBarcode.get(item.barcode)
                const name = product?.name ?? t('unknownProduct')
                return (
                  <li key={item.barcode} className="flex flex-col gap-4 rounded-lg border border-line bg-white p-5">
                    <div className="min-w-0 flex-1">
                      <Link to="/proizvod/$barcode" params={{ barcode: item.barcode }} className="font-semibold text-ink underline-offset-4 hover:underline">
                        {name}
                      </Link>
                      <p className="text-sm text-ink-muted">
                        {product ? [product.brand, product.unit].filter(Boolean).join(' · ') : item.barcode}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <QuantityStepper value={item.qty} name={name} onChange={(qty) => basket.setQty(item.barcode, qty)} />
                      <button type="button" onClick={() => basket.remove(item.barcode)} className="btn btn-secondary">
                        {t('remove')}<span className="sr-only">: {name}</span>
                      </button>
                    </div>
                  </li>
                )
              })}
            </ul>
          </section>
          <section aria-labelledby="compare">
            <h2 id="compare" className="mb-5 font-display text-2xl">{t('compareHeading')}</h2>
            {totals.isPending ? (
              <StateView kind="loading" lines={2} />
            ) : totals.isError ? (
              <StateView kind={totals.error instanceof ApiError && totals.error.status === 0 ? 'offline' : 'error'}
                onRetry={() => void totals.refetch()} />
            ) : toTotals(totals.data).length === 0 ? (
              <StateView kind="empty" />
            ) : (
              <>
                <BasketSummary totals={toTotals(totals.data)} headingLevel={3} />
                {totals.data.split && <BasketSplit split={totals.data.split} names={byBarcode}
                  quantities={new Map(items.map((item) => [item.barcode, item.qty]))} />}
              </>
            )}
          </section>
        </div>
      )}
    </>
  )
}

export const Route = createLazyRoute('/korpa')({ component: () => <WithQuery><BasketPage /></WithQuery> })
