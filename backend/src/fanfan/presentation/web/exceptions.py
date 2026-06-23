import logging
from collections.abc import Mapping
from typing import cast

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from fanfan.core.exceptions.auth import AuthenticationError
from fanfan.core.exceptions.base import (
    AccessDenied,
    AppException,
    Conflict,
    ConstraintViolation,
    NotFound,
    RateLimited,
)
from fanfan.presentation.web.schemas.error import (
    ErrorMessage,
    ValidationErrorDetail,
    ValidationErrorResponse,
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
}


def _resolve_status_code(exc: AppException) -> int:
    """Resolve the HTTP status code using the exception MRO."""
    for exc_type in type(exc).__mro__:
        if exc_type in EXCEPTION_STATUS_MAP:
            return EXCEPTION_STATUS_MAP[cast("type[AppException]", exc_type)]

    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _build_app_exception_headers(exc: AppException) -> Mapping[str, str]:
    retry_after = exc.details.get("retry_after")
    if isinstance(retry_after, int):
        return {"Retry-After": str(retry_after)}

    return {}


def _build_error_content(
    code: str,
    details: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return ErrorMessage(code=code, details=dict(details or {})).model_dump()


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    _ = request

    return JSONResponse(
        status_code=_resolve_status_code(exc),
        content=_build_error_content(exc.code, exc.details),
        headers=dict(_build_app_exception_headers(exc)),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    _ = request

    error_content = ValidationErrorResponse(
        details={
            "errors": [
                ValidationErrorDetail(
                    loc=list(error["loc"]),
                    type=error["type"],
                )
                for error in exc.errors()
            ]
        }
    ).model_dump()

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_content,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    _ = request

    if isinstance(exc.detail, Mapping):
        detail = cast("Mapping[str, object]", exc.detail)
        code = detail.get("code")
        details = detail.get("details")
        if isinstance(code, str) and isinstance(details, Mapping):
            return JSONResponse(
                status_code=exc.status_code,
                content=_build_error_content(
                    code, cast("Mapping[str, object]", details)
                ),
                headers=exc.headers,
            )

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_content(
            code=HTTP_ERROR_CODE,
            details={"status_code": exc.status_code},
        ),
        headers=exc.headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler so unexpected errors still match the ErrorMessage shape.

    Domain (AppException), HTTP, and validation errors are handled above; anything
    that reaches here is an unanticipated bug. We log it (the request id is bound
    by middleware) and return a generic 500 instead of leaking a traceback.
    """
    _ = request
    logger.exception("Unhandled exception while handling request", exc_info=exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_content(code=INTERNAL_ERROR_CODE),
    )
