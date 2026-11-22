import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { Link, createLazyRoute, useNavigate, useSearch } from '@tanstack/react-router'
import { useId } from 'react'
import { ProductCard, StateView } from '../components'
import { useI18n } from '../i18n/I18nProvider'
import { ApiError, PAGE_SIZE, fetchCategories, searchProducts } from '../lib/api'
import { basket, useBasket } from '../lib/basket'
import { usePageMeta } from '../lib/meta'
import { WithQuery } from '../lib/query'

const MAX_OFFSET = 1000

function SearchPage() {
  const { t, tp } = useI18n()
  const { q = '', kategorija } = useSearch({ from: '/pretraga' })
  const navigate = useNavigate({ from: '/pretraga' })
  const inBasket = new Set(useBasket().map((item) => item.barcode))
  const selectId = useId()
  const categories = useQuery({ queryKey: ['categories'], queryFn: fetchCategories })
  // A query of 2+ characters, or a category alone (browsing).
  const ready = q.length >= 2 || kategorija !== undefined
  const categoryName = categories.data?.find((category) => category.code === kategorija)?.name
  const heading = q.length >= 2 ? t('searchTitle', { q }) : (categoryName ?? t('searchHeading'))
  usePageMeta(heading)

  const results = useInfiniteQuery({
    queryKey: ['search', q, kategorija],
    queryFn: ({ pageParam }) => searchProducts(q.length >= 2 ? q : '', kategorija, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.length * PAGE_SIZE
      return loaded < last.total && loaded <= MAX_OFFSET ? loaded : undefined
    },
    enabled: ready,
  })
  const items = results.data?.pages.flatMap((page) => page.items) ?? []
  const total = results.data?.pages[0]?.total ?? 0

  return (
    <>
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">{heading}</h1>
      {!ready ? (
        <p className="mt-4 text-lg text-ink-soft">{t('searchHint')}</p>
      ) : (
        <>
          <div className="mt-6 flex flex-col gap-4">
            <p role="status" className="text-ink-soft">{results.isSuccess ? tp('results', total) : ''}</p>
            <div role="group" aria-labelledby={selectId}>
              <p id={selectId} className="text-sm font-semibold uppercase tracking-wide text-ink-muted">{t('categoryLabel')}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button type="button" aria-pressed={kategorija === undefined}
                  onClick={() => navigate({ search: (previous) => ({ ...previous, kategorija: undefined }) })}
                  className="min-h-11 rounded-full border border-ink-muted bg-white px-4 font-semibold aria-pressed:border-brand aria-pressed:bg-brand aria-pressed:text-white">
                  {t('allCategories')}
                </button>
                {categories.data?.map((category) => (
                  <button key={category.code} type="button" aria-pressed={kategorija === category.code}
                    onClick={() => navigate({ search: (previous) => ({ ...previous, kategorija: category.code }) })}
                    className="min-h-11 rounded-full border border-ink-muted bg-white px-4 font-semibold aria-pressed:border-brand aria-pressed:bg-brand aria-pressed:text-white">
                    {category.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-6">
            {results.isPending ? (
              <StateView kind="loading" />
            ) : results.isError ? (
              <StateView kind={results.error instanceof ApiError && results.error.status === 0 ? 'offline' : 'error'}
                onRetry={() => void results.refetch()} />
            ) : items.length === 0 ? (
              <StateView kind="empty" message={q ? t('emptySearch', { q }) : t('emptyCategory')} />
            ) : (
              <>
                <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {items.map((item) => (
                    <li key={item.barcode} className="flex">
                      <div className="flex-1">
                        <ProductCard
                          product={{
                            barcode: item.barcode, name: item.name, brand: item.brand, unit: item.unit,
                            minPara: item.min_effective_para, maxPara: item.max_effective_para,
                            nFormats: item.n_formats, anyDiscount: item.any_discount, listDate: item.list_date,
                          }}
                          href={`/proizvod/${item.barcode}`}
                          renderLink={(children, className) => (
                            <Link to="/proizvod/$barcode" params={{ barcode: item.barcode }} className={className}>{children}</Link>
                          )}
                          onAdd={(barcode) => basket.add(barcode)}
                          added={inBasket.has(item.barcode)}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
                {results.hasNextPage && (
                  <button type="button" disabled={results.isFetchingNextPage} onClick={() => void results.fetchNextPage()}
                    className="btn btn-secondary mt-6 disabled:opacity-50">
                    {results.isFetchingNextPage ? t('loading') : t('showMore')}
                  </button>
                )}
              </>
            )}
          </div>
        </>
      )}
    </>
  )
}

export const Route = createLazyRoute('/pretraga')({ component: () => <WithQuery><SearchPage /></WithQuery> })
