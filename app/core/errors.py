from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@dataclass
class ProblemError(Exception):
    status: int
    title: str
    detail: str
    type_uri: str = "about:blank"


def problem_response(
    request: Request,
    status: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    errors: list | None = None,
) -> JSONResponse:
    body = {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
        "request_id": getattr(request.state, "request_id", None),
    }
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def handle_problem(request: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(request, exc.status, exc.title, exc.detail, exc.type_uri)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem_response(request, exc.status_code, "HTTP error", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem_response(
            request,
            422,
            "Validation error",
            "The request does not satisfy the API contract.",
            "https://databolico.com/problems/validation",
            jsonable_encoder(exc.errors(), custom_encoder={ValueError: str}),
        )
