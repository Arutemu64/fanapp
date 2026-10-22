import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from fanfan.core.exceptions.auth import AuthenticationError
from fanfan.core.exceptions.base import (
    AccessDenied,
    AppException,
    Conflict,
    ConstraintViolation,
    NotFound,
    RateLimited,
    UpstreamServiceError,
)
from fanfan.presentation.web.schemas.error import (
    PROBLEM_JSON_MEDIA_TYPE,
    VALIDATION_ERROR_CODE,
    ValidationContextValue,
    ValidationErrorDetail,
)

logger = logging.getLogger(__name__)

# Codes the handlers synthesize (not tied to a domain exception). Exposed here so
# the OpenAPI code-enum builder can include them in the client-facing union.
HTTP_ERROR_CODE = "HTTP_ERROR"
INTERNAL_ERROR_CODE = "INTERNAL_ERROR"

# Keyed on semantic marker base classes (defined in core), not on individual
# leaf exceptions. Each concrete exception inherits the marker that fits its
# meaning, and _resolve_status_code() walks the MRO to find it. Adding an
# exception means picking the right marker, not editing this map; a completeness
# test (tests/.../test_exception_status_map.py) fails if anything slips through.
EXCEPTION_STATUS_MAP: dict[type[AppException], int] = {
    ConstraintViolation: status.HTTP_400_BAD_REQUEST,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AccessDenied: status.HTTP_403_FORBIDDEN,
    NotFound: status.HTTP_404_NOT_FOUND,
    Conflict: status.HTTP_409_CONFLICT,
    RateLimited: status.HTTP_429_TOO_MANY_REQUESTS,
    UpstreamServiceError: status.HTTP_502_BAD_GATEWAY,
}


def _resolve_status_code(exc: AppException) -> int:
    """Resolve the HTTP status code using the exception MRO."""
    for exc_type in type(exc).__mro__:
        if exc_type in EXCEPTION_STATUS_MAP:
            return EXCEPTION_STATUS_MAP[cast("type[AppException]", exc_type)]

    return status.HTTP_500_INTERNAL_SERVER_ERROR


def is_expected_error(exc: BaseException) -> bool:
    """True for an error the handlers answer with a status the client can act on.

    Request validation and every domain exception with a semantic marker are
    outcomes, not bugs, so error reporting skips them. A domain exception with no
    marker is the opposite: it was never meant to reach a client, so reaching one
    is a bug worth reporting.
    """
    if isinstance(exc, RequestValidationError):
        return True
    if isinstance(exc, AppException):
        return _resolve_status_code(exc) != status.HTTP_500_INTERNAL_SERVER_ERROR
    return False


def problem_type(code: str) -> str:
    """The RFC 9457 `type` URI for an error code.

    A relative reference with the full path, which RFC 9457 §3.1.1 allows: an
    absolute URI would need the deployment's host, and the client identifies
    a problem by `code` anyway. Nothing is served there yet; consumers are not
    meant to dereference it.
    """
    return "/problems/" + code.lower().replace("_", "-")


def problem_response(
    status_code: int,
    code: str,
    extensions: Mapping[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """An RFC 9457 problem details response for an error `code`."""
    content: dict[str, Any] = dict(extensions or {})
    # The standard members go last so an extension can never overwrite them.
    content.update(
        type=problem_type(code),
        title=HTTPStatus(status_code).phrase,
        status=status_code,
        code=code,
    )
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers,
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


def internal_error_response(exc: Exception) -> JSONResponse:
    """Log an unanticipated error and answer with a generic 500.

    The code and details stay out of the body: they describe our bug, not
    anything the client can act on. The ERROR log is what reaches Sentry (its
    logging integration), with the request id bound by `BindRequestContextMiddleware`.
    """
    # Not `.exception()`: a handler runs outside the `except` block, so it would
    # attach `sys.exc_info()` — None here — instead of `exc` (ruff LOG004).
    logger.error("Unhandled exception while handling request", exc_info=exc)

    return problem_response(status.HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_ERROR_CODE)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    _ = request

    status_code = _resolve_status_code(exc)
    # A domain exception with no marker is internal-only (see the status-map
    # test): reaching a client means a bug, so it is handled like any other.
    if status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        return internal_error_response(exc)

    headers: dict[str, str] | None = None
    retry_after = exc.details.get("retry_after")
    if isinstance(retry_after, int):
        headers = {"Retry-After": str(retry_after)}

    return problem_response(status_code, exc.code, exc.details, headers)


def _scalar_context(ctx: Mapping[str, object]) -> dict[str, ValidationContextValue]:
    # The input itself never goes back (`input` is dropped): it may be a password.
    return {
        key: value
        for key, value in ctx.items()
        if isinstance(value, str | int | float | bool)
    }


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    _ = request

    errors = [
        ValidationErrorDetail(
            loc=list(error["loc"]),
            type=error["type"],
            ctx=_scalar_context(error.get("ctx", {})),
        ).model_dump()
        for error in exc.errors()
    ]
    return problem_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        VALIDATION_ERROR_CODE,
        {"errors": errors},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    _ = request

    if isinstance(exc.detail, Mapping):
        detail = cast("Mapping[str, object]", exc.detail)
        code = detail.get("code")
        details = detail.get("details")
        if isinstance(code, str) and isinstance(details, Mapping):
            return problem_response(
                exc.status_code,
                code,
                cast("Mapping[str, object]", details),
                exc.headers,
            )

    return problem_response(exc.status_code, HTTP_ERROR_CODE, headers=exc.headers)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler so unexpected errors still answer as problem details.

    Starlette runs an `Exception` handler in `ServerErrorMiddleware`, outside
    every other middleware, so its response carries no CORS, request-id or
    security headers. Route errors are therefore caught earlier, by the
    `CatchUnexpectedErrorsMiddleware`; only an error raised by a middleware
    outside that one still lands here.
    """
    _ = request
    return internal_error_response(exc)


def add_exception_handlers(app: FastAPI) -> None:
    # Handlers narrow `exc` to a concrete exception subtype, which Starlette's
    # broad `ExceptionHandler` signature doesn't model — a known false positive.
    app.add_exception_handler(AppException, app_exception_handler)  # ty: ignore[invalid-argument-type]
    # Starlette's HTTPException, not FastAPI's subclass: the router raises the
    # Starlette one for an unknown path (404) or method (405), and only a handler
    # on the base class answers those as problem details too.
    # https://fastapi.tiangolo.com/tutorial/handling-errors/
    app.add_exception_handler(HTTPException, http_exception_handler)  # ty: ignore[invalid-argument-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # ty: ignore[invalid-argument-type]
    # Last resort for an error raised outside `CatchUnexpectedErrorsMiddleware` (in an
    # outer middleware), so even that response stays problem details.
    app.add_exception_handler(Exception, unhandled_exception_handler)
