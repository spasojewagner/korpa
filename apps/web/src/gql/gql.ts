import * as types from './graphql';
import type { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';


type Documents = {
    "query ProductCategories {\n  categories {\n    code\n    name\n  }\n}": typeof types.ProductCategoriesDocument,
    "query ProductDetail($barcode: String!) {\n  asOf\n  product(barcode: $barcode) {\n    barcode\n    name\n    brand\n    unit\n    category {\n      code\n      name\n    }\n    names {\n      rawName\n      retailer {\n        id\n        name\n        slug\n      }\n    }\n    prices {\n      regularPara\n      discountedPara\n      effectivePara\n      unitPricePara\n      vat\n      discountFrom\n      discountTo\n      listDate\n      asOf\n      format {\n        id\n        name\n        retailer {\n          id\n          name\n          slug\n        }\n      }\n    }\n    cheapest {\n      effectivePara\n      listDate\n      asOf\n      format {\n        id\n        name\n      }\n    }\n    history(months: 1) {\n      month\n      regularPara\n      discountedPara\n      listDate\n      asOf\n    }\n    changes(days: 1) {\n      changedOn\n      regularPara\n      discountedPara\n      listDate\n      asOf\n    }\n  }\n}": typeof types.ProductDetailDocument,
    "query ProductsSummary($barcodes: [String!]!) {\n  asOf\n  products(barcodes: $barcodes) {\n    barcode\n    name\n    brand\n    unit\n  }\n}": typeof types.ProductsSummaryDocument,
};
const documents: Documents = {
    "query ProductCategories {\n  categories {\n    code\n    name\n  }\n}": types.ProductCategoriesDocument,
    "query ProductDetail($barcode: String!) {\n  asOf\n  product(barcode: $barcode) {\n    barcode\n    name\n    brand\n    unit\n    category {\n      code\n      name\n    }\n    names {\n      rawName\n      retailer {\n        id\n        name\n        slug\n      }\n    }\n    prices {\n      regularPara\n      discountedPara\n      effectivePara\n      unitPricePara\n      vat\n      discountFrom\n      discountTo\n      listDate\n      asOf\n      format {\n        id\n        name\n        retailer {\n          id\n          name\n          slug\n        }\n      }\n    }\n    cheapest {\n      effectivePara\n      listDate\n      asOf\n      format {\n        id\n        name\n      }\n    }\n    history(months: 1) {\n      month\n      regularPara\n      discountedPara\n      listDate\n      asOf\n    }\n    changes(days: 1) {\n      changedOn\n      regularPara\n      discountedPara\n      listDate\n      asOf\n    }\n  }\n}": types.ProductDetailDocument,
    "query ProductsSummary($barcodes: [String!]!) {\n  asOf\n  products(barcodes: $barcodes) {\n    barcode\n    name\n    brand\n    unit\n  }\n}": types.ProductsSummaryDocument,
};


export function graphql(source: string): unknown;


export function graphql(source: "query ProductCategories {\n  categories {\n    code\n    name\n  }\n}"): (typeof documents)["query ProductCategories {\n  categories {\n    code\n    name\n  }\n}"];

export function graphql(source: "query ProductDetail($barcode: String!) {\n  asOf\n  product(barcode: $barcode) {\n    barcode\n    name\n    brand\n    unit\n    category {\n      code\n      name\n    }\n    names {\n      rawName\n      retailer {\n        id\n        name\n        slug\n      }\n    }\n    prices {\n      regularPara\n      discountedPara\n      effectivePara\n      unitPricePara\n      vat\n      discountFrom\n      discountTo\n      listDate\n      asOf\n      format {\n        id\n        name\n        retailer {\n          id\n          name\n          slug\n        }\n      }\n    }\n    cheapest {\n      effectivePara\n      listDate\n      asOf\n      format {\n        id\n        name\n      }\n    }\n    history(months: 1) {\n      month\n      regularPara\n      discountedPara\n      listDate\n      asOf\n    }\n    changes(days: 1) {\n      changedOn\n      regularPara\n      discountedPara\n      listDate\n      asOf\n    }\n  }\n}"): (typeof documents)["query ProductDetail($barcode: String!) {\n  asOf\n  product(barcode: $barcode) {\n    barcode\n    name\n    brand\n    unit\n    category {\n      code\n      name\n    }\n    names {\n      rawName\n      retailer {\n        id\n        name\n        slug\n      }\n    }\n    prices {\n      regularPara\n      discountedPara\n      effectivePara\n      unitPricePara\n      vat\n      discountFrom\n      discountTo\n      listDate\n      asOf\n      format {\n        id\n        name\n        retailer {\n          id\n          name\n          slug\n        }\n      }\n    }\n    cheapest {\n      effectivePara\n      listDate\n      asOf\n      format {\n        id\n        name\n      }\n    }\n    history(months: 1) {\n      month\n      regularPara\n      discountedPara\n      listDate\n      asOf\n    }\n    changes(days: 1) {\n      changedOn\n      regularPara\n      discountedPara\n      listDate\n      asOf\n    }\n  }\n}"];

export function graphql(source: "query ProductsSummary($barcodes: [String!]!) {\n  asOf\n  products(barcodes: $barcodes) {\n    barcode\n    name\n    brand\n    unit\n  }\n}"): (typeof documents)["query ProductsSummary($barcodes: [String!]!) {\n  asOf\n  products(barcodes: $barcodes) {\n    barcode\n    name\n    brand\n    unit\n  }\n}"];

export function graphql(source: string) {
  return (documents as Record<string, unknown>)[source] ?? {};
}

export type DocumentType<TDocumentNode extends DocumentNode<unknown, never>> = TDocumentNode extends DocumentNode<infer TType, never>  ? TType  : never;