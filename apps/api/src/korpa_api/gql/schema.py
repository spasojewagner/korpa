import strawberry

from korpa_api.gql.limits import extensions
from korpa_api.gql.types import Query

schema = strawberry.Schema(query=Query, extensions=extensions())
