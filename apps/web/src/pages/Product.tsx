import { useQuery } from '@tanstack/react-query'
import { Link, createLazyRoute, useParams } from '@tanstack/react-router'
import { useRef } from 'react'
import { PriceComparison, QuantityStepper, Sparkline, StateView, type MonthPoint } from '../components'
import { ProductDetailDocument, type ProductDetailQuery } from '../gql/graphql'
import { useI18n } from '../i18n/I18nProvider'
import { ApiError, graphql } from '../lib/api'
import { basket, useBasket } from '../lib/basket'
import { usePageMeta } from '../lib/meta'
import { WithQuery } from '../lib/query'

type Product = NonNullable<ProductDetailQuery['product']>

/** Lowest regular price per month across formats (history has no discount windows). */
export function monthlyLows(months: Product['monthlyPrices']): MonthPoint[] {
  return months.map(({ month, minRegularPara }) => ({ month, para: minRegularPara }))
}

function ProductPage() {
  const { t } = useI18n()
  const { barcode } = useParams({ from: '/proizvod/$barcode' })
  const valid = /^[0-9]{13}$/.test(barcode)
  const query = useQuery({
    queryKey: ['product', barcode],
    queryFn: () => graphql(ProductDetailDocument, { barcode }),
    enabled: valid,
  })
  const product = query.data?.product
  usePageMeta(product?.name ?? t('productHeading'))

  if (!valid || (query.isSuccess && !product)) {
    return (
      <>
        <h1 className="text-2xl font-semibold">{t('productNotFound')}</h1>
        <p className="mt-4 text-ink-soft">{t('productNotFoundText')}</p>
        <Link to="/pretraga" className="mt-4 inline-block text-brand underline underline-offset-2">{t('goToSearch')}</Link>
      </>
    )
  }
  if (query.isPending) return <StateView kind="loading" lines={2} />
  if (query.isError || !product) {
    const offline = query.error instanceof ApiError && query.error.status === 0
    return <StateView kind={offline ? 'offline' : 'error'} onRetry={() => void query.refetch()} />
  }
  return <ProductView product={product} />
}

function ProductView({ product }: { product: Product }) {
  const { t } = useI18n()
  const item = useBasket().find((entry) => entry.barcode === product.barcode)
  const history = monthlyLows(product.monthlyPrices)
  const actions = useRef<HTMLDivElement>(null)
  const add = () => {
    basket.add(product.barcode)
    // The button is replaced by the quantity stepper; keep keyboard focus there.
    requestAnimationFrame(() => actions.current?.querySelector('input')?.focus())
  }
  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold sm:text-3xl">{product.name}</h1>
        <p className="text-ink-soft">
          {[product.brand, product.unit, product.category.name].filter(Boolean).join(' · ')}
        </p>
        <p className="text-sm text-ink-muted">{t('barcode')}: <span className="tabular-nums">{product.barcode}</span></p>
        <div ref={actions} className="mt-2 flex flex-wrap items-center gap-4">
          {item ? (
            <>
              <QuantityStepper value={item.qty} name={product.name} onChange={(qty) => basket.setQty(product.barcode, qty)} />
              <Link to="/korpa" className="text-brand underline underline-offset-2">{t('goToBasket')}</Link>
            </>
          ) : (
            <button type="button" onClick={add}
              className="min-h-11 rounded-md bg-brand px-5 font-semibold text-white hover:bg-brand-hover">
              {t('addToBasket')}
            </button>
          )}
        </div>
      </header>

      <section aria-labelledby="prices">
        <h2 id="prices" className="mb-3 text-xl font-semibold">{t('pricesHeading')}</h2>
        <PriceComparison unit={product.unit} rows={product.prices.map((price) => ({
          formatId: price.format.id,
          retailer: price.format.retailer.name,
          format: price.format.name,
          para: price.effectivePara,
          regularPara: price.regularPara,
          unitPara: price.unitPricePara,
          discountTo: price.discountTo,
          listDate: price.listDate,
        }))} />
      </section>

      <section aria-labelledby="history">
        <h2 id="history" className="mb-3 text-xl font-semibold">{t('historyHeading')}</h2>
        {history.length >= 2 ? <Sparkline points={history} /> : <p className="text-ink-soft">{t('noHistory')}</p>}
      </section>

      {product.names.length > 0 && (
        <details className="rounded-lg bg-paper-raised p-4">
          <summary className="cursor-pointer font-semibold">{t('namesHeading')}</summary>
          <ul className="mt-3 flex flex-col gap-1 text-ink-soft">
            {product.names.map((name) => (
              <li key={`${name.retailer.id}-${name.rawName}`}>
                <span className="font-semibold text-ink">{name.retailer.name}:</span> {name.rawName}
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  )
}

export const Route = createLazyRoute('/proizvod/$barcode')({ component: () => <WithQuery><ProductPage /></WithQuery> })
