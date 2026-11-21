# REST and read-only GraphQL

Status: accepted for the initial public API.

Search, basket comparison, categories and data quality have small, predictable response
shapes. REST gives these operations explicit input contracts and straightforward HTTP
caching: successful GET responses can be cached publicly for five minutes. Basket
comparison uses POST because its bounded item list belongs in a request body.

Product detail needs a variable combination of published names, formats, retailer names,
current prices and historical observations. A query-only GraphQL endpoint lets callers
select that nested data in one request. There is no mutation or subscription schema.
Both transports use the existing database tables, one async session per request, integer
para, source dates, and the same effective-price SQL expression. Historical tables do not
retain discount windows, so they expose recorded amounts rather than an invented
historical effective price.

Request-local DataLoaders batch each relationship and prevent caches leaking between
requests. Concurrent loader batches serialize access to their shared session. A database
event test requires the same number of SQL statements for one and twenty products,
including prices, formats, retailers and history, with a ceiling of eight statements.

Depth six, fifteen aliases, one thousand tokens, bounded inputs and a maximum static
cost of five thousand constrain expensive graph expansion before resolution. Every field
costs one; list children multiply by their documented result cap. Oversized result sets
fail explicitly rather than returning incomplete comparisons. Introspection remains
available; the interactive editor is enabled only in development. Rejected operations
use the shared RFC 9457 error contract without partial data.

Versioned SDL, OpenAPI and typed client artifacts make contract changes reviewable.
CI exports the schemas, regenerates clients and rejects drift before its normal checks.
Frontend comparison pages and deployment remain separate work.
