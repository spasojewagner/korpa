import json
import os
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import GraphQLRouter
from strawberry.http import GraphQLHTTPResponse
from strawberry.types import ExecutionResult

from korpa_api.database import session
from korpa_api.gql.context import Context
from korpa_api.gql.schema import schema
from korpa_api.problems import problem


class Envelope(BaseModel):
    query: str = Field(min_length=1, max_length=64000)
    variables: dict[str, object] | None = None
    operationName: str | None = Field(default=None, max_length=100)


async def context(database: Annotated[AsyncSession, Depends(session)]) -> Context:
    return Context(database)


class ReadRouter(GraphQLRouter[Context, None]):
    async def process_result(
        self, request: Request, result: ExecutionResult
    ) -> GraphQLHTTPResponse:
        if result.errors:
            error = result.errors[0]
            original = error.original_error
            if isinstance(original, (SQLAlchemyError, ConnectionError)):
                raise HTTPException(503, "Price data is temporarily unavailable")
            if isinstance(original, ValidationError):
                fields = ", ".join(str(item["loc"][0]) for item in original.errors())
                raise HTTPException(422, "Invalid GraphQL arguments: " + fields)
            if original is not None and not isinstance(original, ValueError):
                raise HTTPException(500, "An unexpected error prevented this query")
            raise HTTPException(422 if original else 400, error.message)
        return await super().process_result(request, result)


def make_router() -> ReadRouter:
    return ReadRouter(
        schema,
        context_getter=context,
        graphql_ide="graphiql" if os.getenv("ENV") == "dev" else None,
        subscription_protocols=(),
    )


async def validate_request(request: Request) -> JSONResponse | None:
    try:
        if request.method == "POST":
            body = await request.body()
            if len(body) > 256000:
                return problem(request, 413, "GraphQL request exceeds 256000 bytes")
            Envelope.model_validate(json.loads(body))
        elif request.method == "GET" and "query" in request.query_params:
            Envelope.model_validate(
                {
                    "query": request.query_params["query"],
                    "variables": json.loads(request.query_params.get("variables", "null")),
                    "operationName": request.query_params.get("operationName"),
                }
            )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return problem(request, 400, "GraphQL request must contain valid JSON")
    except ValidationError:
        return problem(request, 422, "Invalid GraphQL request envelope")
    return None
