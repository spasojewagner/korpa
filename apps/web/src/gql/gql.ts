import * as types from './graphql';




type Documents = {
    "query ProductCategories {\n  categories {\n    code\n    name\n  }\n}": typeof types.ProductCategoriesDocument,
    "query ProductDetail($barcode: String!) {\n  asOf\n  product(barcode: $barcode) {\n    barcode\n    name\n    brand\n    unit\n    category {\n      code\n      name\n    }\n    names {\n      rawName\n      retailer {\n        id\n        name\n        slug\n      }\n    }\n    prices {\n      regularPara\n      discountedPara\n      effectivePara\n      unitPricePara\n      discountFrom\n      discountTo\n      listDate\n      format {\n        id\n        name\n        retailer {\n          id\n          name\n          slug\n        }\n      }\n    }\n    history(months: 12) {\n      month\n      regularPara\n    }\n  }\n}": typeof types.ProductDetailDocument,
    "query ProductsSummary($barcodes: [String!]!) {\n  asOf\n  products(barcodes: $barcodes) {\n    barcode\n    name\n    brand\n    unit\n  }\n}": typeof types.ProductsSummaryDocument,
};
const documents: Documents = {
    "query ProductCategories {\n  categories {\n    code\n    name\n  }\n}": types.ProductCategoriesDocument,
    "query ProductDetail($barcode: String!) {\n  asOf\n  product(barcode: $barcode) {\n    barcode\n    name\n    brand\n    unit\n    category {\n      code\n      name\n    }\n    names {\n      rawName\n      retailer {\n        id\n        name\n        slug\n      }\n    }\n    prices {\n      regularPara\n      discountedPara\n      effectivePara\n      unitPricePara\n      discountFrom\n      discountTo\n      listDate\n      format {\n        id\n        name\n        retailer {\n          id\n          name\n          slug\n        }\n      }\n    }\n    history(months: 12) {\n      month\n      regularPara\n    }\n  }\n}": types.ProductDetailDocument,
    "query ProductsSummary($barcodes: [String!]!) {\n  asOf\n  products(barcodes: $barcodes) {\n    barcode\n    name\n    brand\n    unit\n  }\n}": types.ProductsSummaryDocument,
};


export function graphql(source: "query ProductCategories {\n  categories {\n    code\n    name\n  }\n}"): typeof import('./graphql').ProductCategoriesDocument;

export function graphql(source: "query ProductDetail($barcode: String!) {\n  asOf\n  product(barcode: $barcode) {\n    barcode\n    name\n    brand\n    unit\n    category {\n      code\n      name\n    }\n    names {\n      rawName\n      retailer {\n        id\n        name\n        slug\n      }\n    }\n    prices {\n      regularPara\n      discountedPara\n      effectivePara\n      unitPricePara\n      discountFrom\n      discountTo\n      listDate\n      format {\n        id\n        name\n        retailer {\n          id\n          name\n          slug\n        }\n      }\n    }\n    history(months: 12) {\n      month\n      regularPara\n    }\n  }\n}"): typeof import('./graphql').ProductDetailDocument;

export function graphql(source: "query ProductsSummary($barcodes: [String!]!) {\n  asOf\n  products(barcodes: $barcodes) {\n    barcode\n    name\n    brand\n    unit\n  }\n}"): typeof import('./graphql').ProductsSummaryDocument;


export function graphql(source: string) {
  return (documents as Record<string, unknown>)[source] ?? {};
}
