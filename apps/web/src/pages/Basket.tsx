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
      <h1 className="text-2xl font-semibold">{t('basketHeading')}</h1>
      <BasketAssistant />
      {items.length === 0 ? (
        <div className="mt-4 flex flex-col items-start gap-3">
          <p className="text-ink-soft">{t('basketEmpty')}</p>
          <Link to="/pretraga" className="text-brand underline underline-offset-2">{t('goToSearch')}</Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-10 lg:grid-cols-2">
          <section aria-labelledby="items">
            <h2 id="items" className="mb-3 text-xl font-semibold">{t('basketItemsHeading')}</h2>
            <ul className="flex flex-col">
              {items.map((item) => {
                const product = byBarcode.get(item.barcode)
                const name = product?.name ?? t('unknownProduct')
                return (
                  <li key={item.barcode} className="flex flex-wrap items-center justify-between gap-3 border-b border-line py-3">
                    <div className="min-w-0 flex-1">
                      <Link to="/proizvod/$barcode" params={{ barcode: item.barcode }} className="font-semibold text-ink underline-offset-4 hover:underline">
                        {name}
                      </Link>
                      <p className="text-sm text-ink-muted">
                        {product ? [product.brand, product.unit].filter(Boolean).join(' · ') : item.barcode}
                      </p>
                    </div>
                    <QuantityStepper value={item.qty} name={name} onChange={(qty) => basket.setQty(item.barcode, qty)} />
                    <button type="button" onClick={() => basket.remove(item.barcode)}
                      className="min-h-11 px-2 text-danger underline underline-offset-2">
                      {t('remove')}<span className="sr-only">: {name}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
          <section aria-labelledby="compare">
            <h2 id="compare" className="mb-3 text-xl font-semibold">{t('compareHeading')}</h2>
            {totals.isPending ? (
              <StateView kind="loading" lines={2} />
            ) : totals.isError ? (
              <StateView kind={totals.error instanceof ApiError && totals.error.status === 0 ? 'offline' : 'error'}
                onRetry={() => void totals.refetch()} />
            ) : toTotals(totals.data).length === 0 ? (
              <StateView kind="empty" />
            ) : (
              <BasketSummary totals={toTotals(totals.data)} headingLevel={3} />
            )}
          </section>
        </div>
      )}
    </>
  )
}

export const Route = createLazyRoute('/korpa')({ component: () => <WithQuery><BasketPage /></WithQuery> })
