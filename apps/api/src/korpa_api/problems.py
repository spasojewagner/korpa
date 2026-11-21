from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from korpa_api.schemas import Problem


def problem(request: Request, status: int, detail: str, **extensions: object) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content=Problem.model_validate(
            {
                "type": "about:blank",
                "title": HTTPStatus(status).phrase,
                "status": status,
                "detail": detail,
                "instance": request.url.path,
                **extensions,
            }
        ).model_dump(exclude_none=True),
        headers={"Cache-Control": "no-store"},
    )


def problem_responses() -> dict[int | str, dict[str, object]]:
    return {
        status: {
            "description": HTTPStatus(status).phrase,
            "content": {"application/problem+json": {"schema": Problem.model_json_schema()}},
        }
        for status in (422, 500, 503)
    }


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem(
            request,
            422,
            "Request validation failed",
            errors=[
                {
                    "location": list(error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ],
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        response = problem(request, exc.status_code, str(exc.detail))
        response.headers.update(exc.headers or {})
        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return problem(request, 503, "Price data is temporarily unavailable")

    @app.exception_handler(ConnectionError)
    async def connection_error(request: Request, exc: ConnectionError) -> JSONResponse:
        return problem(request, 503, "Price data is temporarily unavailable")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return problem(request, 500, "An unexpected error prevented this request")
