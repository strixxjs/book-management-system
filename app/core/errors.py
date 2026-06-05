import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = structlog.get_logger()


class FieldError(BaseModel):
    field: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[FieldError] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[FieldError] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Catches all HTTPException (404, 409, 401, 400, ...) raised anywhere
    in the application and wraps them in the unified error shape.

    We map status codes to short snake_case codes so clients can branch
    on a stable string rather than an integer.
    """
    code_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
    }
    code = code_map.get(exc.status_code, "error")
    return _error_response(exc.status_code, code, exc.detail)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    FastAPI raises RequestValidationError for request body / query param
    validation failures (Pydantic). Default response is 422 with a nested
    list that is hard to parse on the client side.

    We flatten it to a list of {field, message} pairs.

    loc[0] is usually "body" or "query" — we skip it and join the rest
    so the field path looks like "year" or "author.name", not
    "body.year" or "body.author.name".
    """
    details = []
    for error in exc.errors():
        loc = error.get("loc", [])
        # skip the first element ("body", "query", "path") — it's noise
        field_parts = (
            [str(p) for p in loc[1:]]
            if len(loc) > 1
            else [str(loc[0])]
            if loc
            else ["unknown"]
        )
        details.append(FieldError(field=".".join(field_parts), message=error["msg"]))

    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed",
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        path=request.url.path,
        method=request.method,
    )
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An unexpected error occurred",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Single entry point — called once in main.py.
    Keeps main.py clean: it does not import individual handlers.
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
