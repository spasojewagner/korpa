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
      <h1 className="text-2xl font-semibold">{heading}</h1>
      {!ready ? (
        <p className="mt-4 text-ink-soft">{t('searchHint')}</p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
            <p role="status" className="text-ink-soft">{results.isSuccess ? tp('results', total) : ''}</p>
            <div className="flex flex-col gap-1">
              <label htmlFor={selectId} className="text-sm font-semibold">{t('categoryLabel')}</label>
              <select id={selectId} value={kategorija ?? ''}
                onChange={(event) => navigate({
                  search: (previous) => ({ ...previous, kategorija: event.target.value ? Number(event.target.value) : undefined }),
                })}
                className="min-h-11 rounded-md border border-ink-muted bg-white px-3">
                <option value="">{t('allCategories')}</option>
                {categories.data?.map((category) => (
                  <option key={category.code} value={category.code}>{category.name}</option>
                ))}
              </select>
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
                    className="mt-6 min-h-11 rounded-md border border-brand px-5 font-semibold text-brand hover:bg-brand-subtle disabled:opacity-50">
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
