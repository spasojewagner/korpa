import type { ProductDetailQuery, ProductsSummaryQuery } from '../src/gql/graphql'
import type { IndexResponse, SignalsResponse } from '../src/lib/analytics'
import type { Schemas } from '../src/lib/api'

const asOf = '2026-11-21'
const alfa = { id: 1, name: 'Alfa', slug: 'alfa' }
const beta = { id: 2, name: 'Beta', slug: 'beta' }
export const MILK = '8600000000001'

export const search: Schemas['SearchResponse'] = {
  as_of: asOf,
  total: 2,
  items: [
    { barcode: MILK, name: 'Mleko 2,8% 1 l', brand: 'Imlek', unit: 'l', category_code: 2, min_effective_para: 13999,
      max_effective_para: 16999, n_formats: 2, any_discount: true, list_date: '2026-11-20' },
    { barcode: '8600000000002', name: 'Mleko 0,9% 1 l', brand: 'Imlek', unit: 'l', category_code: 2, min_effective_para: 12999,
      max_effective_para: 12999, n_formats: 1, any_discount: false, list_date: '2026-11-20' },
  ],
}

export const categories: Schemas['CategoryItem'][] = [{ code: 2, name: 'Mleko i mlečni proizvodi', n_products: 2 }]

export const quality: Schemas['QualityResponse'] = {
  as_of: asOf,
  name_variants: { barcodes: 1, share_of_products: 0.5, examples: [
    { barcode: MILK, names: [{ retailer: 'Alfa', name: 'MLEKO 2,8% 1L IMLEK' },
      { retailer: 'Beta', name: 'Mleko 2,8% 1 l' }] },
  ] },
  retailers: [{
    id: 1, name: 'Alfa', slug: 'alfa', status: 'partial', http_status: 200, rows_total: 1000, rows_valid: 930,
    errors: { price: 70 }, suspected_errors: { price_outlier: 3 }, errors_by_rule: { price: 70 }, deviations: { price_decimals: 120 }, profile: 'compat-2026-11.2',
    finished_at: '2026-11-21T03:00:00Z', list_date: '2026-11-20', days_since_list_date: 1,
  }],
}

export const product: ProductDetailQuery = {
  asOf,
  product: {
    barcode: MILK, name: 'Mleko 2,8% 1 l', brand: 'Imlek', unit: 'l',
    category: { code: 2, name: 'Mleko i mlečni proizvodi' },
    names: [{ rawName: 'MLEKO 2,8% 1L IMLEK', retailer: alfa }],
    prices: [
      { regularPara: 15999, discountedPara: 13999, effectivePara: 13999, unitPricePara: 13999, discountFrom: '2026-11-15',
        discountTo: '2026-11-30', listDate: '2026-11-20', format: { id: 1, name: 'Alfa Hiper', retailer: alfa } },
      { regularPara: 16999, discountedPara: null, effectivePara: 16999, unitPricePara: 16999, discountFrom: null,
        discountTo: null, listDate: '2026-11-20', format: { id: 2, name: 'Beta Market', retailer: beta } },
    ],
    monthlyPrices: [
      { month: '2026-09-01', minRegularPara: 15499 },
      { month: '2026-10-01', minRegularPara: 15999 },
      { month: '2026-11-01', minRegularPara: 15999 },
    ],
  },
}

export const summary: ProductsSummaryQuery = {
  asOf,
  products: [{ barcode: MILK, name: 'Mleko 2,8% 1 l', brand: 'Imlek', unit: 'l' }],
}

export const basket: Schemas['BasketResponse'] = {
  as_of: asOf,
  split: { total_para: 13999, saving_vs_best_para: 0, n_formats: 1,
    items: [{ barcode: MILK, format: { id: 1, name: 'Alfa Hiper' }, price_para: 13999, list_date: '2026-11-20' }] },
  retailers: [
    { ...alfa, formats: [{ id: 1, name: 'Alfa Hiper', total_para: 13999, found_barcodes: [MILK], missing_barcodes: [],
      complete: true, rank: 1, list_date_min: '2026-11-20', list_date_max: '2026-11-20' }] },
    { ...beta, formats: [{ id: 2, name: 'Beta Market', total_para: 12999, found_barcodes: ['8600000000002'],
      missing_barcodes: [MILK], complete: false, rank: 2, list_date_min: '2026-11-20', list_date_max: '2026-11-20' }] },
  ],
}

export const priceIndex: IndexResponse = {
  as_of: asOf,
  base_month: '2026-11-01',
  notes: { model: 'test-model', items: ['Ukupni indeks je 101,4, što je rast od 1,4 % od novembra 2026.'] },
  categories: [
    { code: 0, name: 'Sve kategorije', points: [
      { month: '2026-11-01', value: 100, n_products: 61234, n_excluded: 0, provisional: false },
      { month: '2026-11-21', value: 101.4, n_products: 59876, n_excluded: 12, provisional: true },
    ] },
    { code: 2, name: 'Mleko i mlečni proizvodi', points: [
      { month: '2026-11-01', value: 100, n_products: 812, n_excluded: 0, provisional: false },
      { month: '2026-11-21', value: 97.5, n_products: 790, n_excluded: 1, provisional: true },
    ] },
    { code: 9, name: 'Sirće', points: [
      { month: '2026-11-21', value: null, n_products: 12, n_excluded: 0, provisional: true },
    ] },
  ],
}

export const signals: SignalsResponse = {
  as_of: asOf,
  items: [
    { type: 'discount_after_jump', barcode: MILK, name: 'Mleko 2,8% 1 l', retailer: 'Alfa',
      format: 'Alfa Hiper', date: '2026-11-10', price_para: 18000, reference_para: 15000,
      ratio: 1.2, old_regular_para: 15000, new_regular_para: 18000, discounted_para: 14900,
      rise_date: '2026-11-10', disc_from: '2026-11-15', as_of: asOf },
    { type: 'jump', barcode: MILK, name: 'Mleko 2,8% 1 l', retailer: 'Alfa', format: 'Alfa Hiper', date: '2026-11-20',
      price_para: 18999, reference_para: 14999, ratio: 1.27 },
    { type: 'outlier', barcode: '8600000000002', name: 'Mleko 0,9% 1 l', retailer: 'Beta', format: 'Beta Market',
      date: '2026-11-20', price_para: 24999, reference_para: 15999, ratio: 1.56 },
  ],
}
