import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from korpa_api.database import async_database_url
from korpa_api.gql.router import make_router, validate_request
from korpa_api.problems import install_problem_handlers, problem, problem_responses
from korpa_api.routes import router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_async_engine(async_database_url(), pool_pre_ping=True)
    app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Korpa", lifespan=lifespan, responses=problem_responses())
install_problem_handlers(app)
app.include_router(router)
app.include_router(make_router(), prefix="/graphql")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        s.strip()
        for s in (os.getenv("CORS_ORIGINS") or "http://localhost:5173,http://127.0.0.1:5173").split(
            ","
        )
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)


@app.middleware("http")
async def cache_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    if request.url.path.rstrip("/") == "/graphql":
        rejected = await validate_request(request)
        if rejected is not None:
            return rejected
    response = await call_next(request)
    if (
        request.url.path.rstrip("/") == "/graphql"
        and response.status_code >= 400
        and (response.headers.get("content-type", "").split(";")[0] != "application/problem+json")
    ):
        return problem(request, response.status_code, "GraphQL request could not be processed")
    if request.method == "GET" and response.status_code < 400:
        response.headers["Cache-Control"] = "public, max-age=300"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
