export interface paths {
    "/api/basket": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Basket */
        post: operations["basket_api_basket_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Categories */
        get: operations["categories_api_categories_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/quality": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Quality */
        get: operations["quality_api_quality_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Search
         * @description Search current-priced products by text and/or category.
         *
         *     At least one of q or category is required. With category alone, order by number of
         *     current retail formats descending, then name; barcode breaks ties for stable pagination.
         *     Text queries retain relevance ranking, optionally filtered by category.
         */
        get: operations["search_api_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** BasketFormat */
        BasketFormat: {
            /** Complete */
            complete: boolean;
            /** Found Barcodes */
            found_barcodes: string[];
            /** Id */
            id: number;
            /** List Date Max */
            list_date_max: string | null;
            /** List Date Min */
            list_date_min: string | null;
            /** Missing Barcodes */
            missing_barcodes: string[];
            /** Name */
            name: string;
            /** Rank */
            rank: number;
            /** Total Para */
            total_para: number;
        };
        /** BasketItem */
        BasketItem: {
            /** Barcode */
            barcode: string;
            /** Qty */
            qty: number;
        };
        /** BasketRequest */
        BasketRequest: {
            /** Items */
            items: components["schemas"]["BasketItem"][];
        };
        /** BasketResponse */
        BasketResponse: {
            /**
             * As Of
             * Format: date
             */
            as_of: string;
            /** Retailers */
            retailers: components["schemas"]["BasketRetailer"][];
        };
        /** BasketRetailer */
        BasketRetailer: {
            /** Formats */
            formats: components["schemas"]["BasketFormat"][];
            /** Id */
            id: number;
            /** Name */
            name: string;
            /** Slug */
            slug: string;
        };
        /** CategoryItem */
        CategoryItem: {
            /** Code */
            code: number;
            /** N Products */
            n_products: number;
            /** Name */
            name: string;
        };
        /** QualityItem */
        QualityItem: {
            /** Days Since List Date */
            days_since_list_date: number | null;
            /** Deviations */
            deviations: {
                [key: string]: number;
            };
            /** Errors */
            errors: {
                [key: string]: number;
            };
            /** Errors By Rule */
            errors_by_rule: {
                [key: string]: number;
            };
            /** Finished At */
            finished_at: string | null;
            /** Http Status */
            http_status: number | null;
            /** Id */
            id: number;
            /** List Date */
            list_date: string | null;
            /** Name */
            name: string;
            /** Profile */
            profile: string | null;
            /** Rows Total */
            rows_total: number | null;
            /** Rows Valid */
            rows_valid: number | null;
            /** Slug */
            slug: string;
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "partial" | "failed" | "never";
        };
        /** QualityResponse */
        QualityResponse: {
            /**
             * As Of
             * Format: date
             */
            as_of: string;
            /** Retailers */
            retailers: components["schemas"]["QualityItem"][];
        };
        /** SearchItem */
        SearchItem: {
            /** Any Discount */
            any_discount: boolean;
            /** Barcode */
            barcode: string;
            /** Brand */
            brand: string;
            /** Category Code */
            category_code: number;
            /**
             * List Date
             * Format: date
             */
            list_date: string;
            /** Max Effective Para */
            max_effective_para: number;
            /** Min Effective Para */
            min_effective_para: number;
            /** N Formats */
            n_formats: number;
            /** Name */
            name: string;
            /** Unit */
            unit: string;
        };
        /** SearchResponse */
        SearchResponse: {
            /**
             * As Of
             * Format: date
             */
            as_of: string;
            /** Items */
            items: components["schemas"]["SearchItem"][];
            /** Total */
            total: number;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    basket_api_basket_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BasketRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BasketResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
        };
    };
    categories_api_categories_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryItem"][];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
        };
    };
    quality_api_quality_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QualityResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
        };
    };
    search_api_search_get: {
        parameters: {
            query?: {
                category?: number | null;
                limit?: number;
                offset?: number;
                /** @description Text query; required unless category is supplied. */
                q?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": {
                        /** Detail */
                        detail: string;
                        /** Errors */
                        errors?: {
                            [key: string]: string | (string | number)[];
                        }[] | null;
                        /** Instance */
                        instance: string;
                        /** Status */
                        status: number;
                        /** Title */
                        title: string;
                        /**
                         * Type
                         * @default about:blank
                         */
                        type: string;
                    };
                };
            };
        };
    };
}
