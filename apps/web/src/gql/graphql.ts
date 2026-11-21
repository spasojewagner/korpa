
type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };

export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
import type { DocumentTypeDecoration } from '@graphql-typed-document-node/core';
export type ProductCategoriesQueryVariables = Exact<{ [key: string]: never; }>;


export type ProductCategoriesQuery = { categories: Array<{ code: number, name: string }> };

export type ProductDetailQueryVariables = Exact<{
  barcode: string;
}>;


export type ProductDetailQuery = { asOf: string, product: { barcode: string, name: string, brand: string, unit: string, category: { code: number, name: string }, names: Array<{ rawName: string, retailer: { id: number, name: string, slug: string } }>, prices: Array<{ regularPara: number, discountedPara: number | null, effectivePara: number, unitPricePara: number, discountFrom: string | null, discountTo: string | null, listDate: string, format: { id: number, name: string, retailer: { id: number, name: string, slug: string } } }>, history: Array<{ month: string, regularPara: number }> } | null };

export type ProductsSummaryQueryVariables = Exact<{
  barcodes: Array<string> | string;
}>;


export type ProductsSummaryQuery = { asOf: string, products: Array<{ barcode: string, name: string, brand: string, unit: string } | null> };

export class TypedDocumentString<TResult, TVariables>
  extends String
  implements DocumentTypeDecoration<TResult, TVariables>
{
  __apiType?: NonNullable<DocumentTypeDecoration<TResult, TVariables>['__apiType']>;
  private value: string;
  public __meta__?: Record<string, unknown> | undefined;

  constructor(value: string, __meta__?: Record<string, unknown> | undefined) {
    super(value);
    this.value = value;
    this.__meta__ = __meta__;
  }

  override toString(): string & DocumentTypeDecoration<TResult, TVariables> {
    return this.value;
  }
}

export const ProductCategoriesDocument = new TypedDocumentString(`
    query ProductCategories {
  categories {
    code
    name
  }
}
    `) as unknown as TypedDocumentString<ProductCategoriesQuery, ProductCategoriesQueryVariables>;
export const ProductDetailDocument = new TypedDocumentString(`
    query ProductDetail($barcode: String!) {
  asOf
  product(barcode: $barcode) {
    barcode
    name
    brand
    unit
    category {
      code
      name
    }
    names {
      rawName
      retailer {
        id
        name
        slug
      }
    }
    prices {
      regularPara
      discountedPara
      effectivePara
      unitPricePara
      discountFrom
      discountTo
      listDate
      format {
        id
        name
        retailer {
          id
          name
          slug
        }
      }
    }
    history(months: 12) {
      month
      regularPara
    }
  }
}
    `) as unknown as TypedDocumentString<ProductDetailQuery, ProductDetailQueryVariables>;
export const ProductsSummaryDocument = new TypedDocumentString(`
    query ProductsSummary($barcodes: [String!]!) {
  asOf
  products(barcodes: $barcodes) {
    barcode
    name
    brand
    unit
  }
}
    `) as unknown as TypedDocumentString<ProductsSummaryQuery, ProductsSummaryQueryVariables>;