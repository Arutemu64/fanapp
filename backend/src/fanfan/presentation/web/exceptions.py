import logging
from collections.abc import Mapping
from typing import cast

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from fanfan.core.exceptions.auth import (
    AuthenticationError,
    IncorrectPassword,
    InvalidCredentials,
    InvalidOtpCode,
    InvalidTelegramAuthPayload,
    UserNotAuthenticated,
)
from fanfan.core.exceptions.base import AccessDenied, AppException
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed
from fanfan.core.exceptions.nominations import NominationNotFound
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.push_sub import (
    PushSubscriptionAlreadyExists,
    PushSubscriptionNotFound,
)
from fanfan.core.exceptions.rate_limit import (
    EmailCodeRequestTooFast,
    TooManyAttempts,
)
from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    EventNotFound,
    OutdatedScheduleChange,
    SameEventsAreNotAllowed,
    ScheduleChangeNotFound,
    ScheduleEditTooFast,
    SkippedEventNotAllowed,
)
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.exceptions.subscriptions import (
    SubscriptionAlreadyExists,
    SubscriptionNotFound,
)
from fanfan.core.exceptions.tickets import (
    TicketAlreadyUsed,
    TicketNotFound,
    UserAlreadyHasTicketLinked,
)
from fanfan.core.exceptions.users import (
    EmailAlreadyExists,
    InvalidEmail,
    TelegramAlreadyLinkedToAnotherUser,
    TelegramCannotBeUnlinkedWithoutEmail,
    UserAlreadyExists,
    UserAlreadyHasTelegramLinked,
    UserHasNoEmail,
    UsernameAlreadyTaken,
    UsernameProfanity,
    UserNotFound,
)
from fanfan.core.exceptions.votes import VoteAlreadyExists, VoteNotFound
from fanfan.presentation.web.schemas.error import (
    ErrorMessage,
    ValidationErrorDetail,
    ValidationErrorResponse,
)

logger = logging.getLogger(__name__)

EXCEPTION_STATUS_MAP: dict[type[AppException], int] = {
    # 400 Bad Request
    InvalidOtpCode: status.HTTP_400_BAD_REQUEST,
    InvalidTelegramAuthPayload: status.HTTP_400_BAD_REQUEST,
    CurrentEventNotAllowed: status.HTTP_400_BAD_REQUEST,
    SameEventsAreNotAllowed: status.HTTP_400_BAD_REQUEST,
    SkippedEventNotAllowed: status.HTTP_400_BAD_REQUEST,
    UsernameProfanity: status.HTTP_400_BAD_REQUEST,
    # Defensive: format validation normally happens at the Pydantic boundary
    # (EmailStr), but the Email value object enforces its own invariant. Map it
    # so any path that builds an Email from looser input fails as 400, not 500.
    InvalidEmail: status.HTTP_400_BAD_REQUEST,
    # 401 Unauthorized
    UserNotAuthenticated: status.HTTP_401_UNAUTHORIZED,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    IncorrectPassword: status.HTTP_401_UNAUTHORIZED,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    # 403 Forbidden
    AccessDenied: status.HTTP_403_FORBIDDEN,
    CaptchaVerificationFailed: status.HTTP_403_FORBIDDEN,
    # 404 Not Found
    UserNotFound: status.HTTP_404_NOT_FOUND,
    EventNotFound: status.HTTP_404_NOT_FOUND,
    NominationNotFound: status.HTTP_404_NOT_FOUND,
    ParticipantNotFound: status.HTTP_404_NOT_FOUND,
    PushSubscriptionNotFound: status.HTTP_404_NOT_FOUND,
    SubscriptionNotFound: status.HTTP_404_NOT_FOUND,
    TicketNotFound: status.HTTP_404_NOT_FOUND,
    VoteNotFound: status.HTTP_404_NOT_FOUND,
    ScheduleChangeNotFound: status.HTTP_404_NOT_FOUND,
    AppSettingsNotFound: status.HTTP_404_NOT_FOUND,
    # 409 Conflict
    UserAlreadyExists: status.HTTP_409_CONFLICT,
    UsernameAlreadyTaken: status.HTTP_409_CONFLICT,
    EmailAlreadyExists: status.HTTP_409_CONFLICT,
    OutdatedScheduleChange: status.HTTP_409_CONFLICT,
    VoteAlreadyExists: status.HTTP_409_CONFLICT,
    SubscriptionAlreadyExists: status.HTTP_409_CONFLICT,
    PushSubscriptionAlreadyExists: status.HTTP_409_CONFLICT,
    TicketAlreadyUsed: status.HTTP_409_CONFLICT,
    UserAlreadyHasTicketLinked: status.HTTP_409_CONFLICT,
    UserHasNoEmail: status.HTTP_409_CONFLICT,
    TelegramCannotBeUnlinkedWithoutEmail: status.HTTP_409_CONFLICT,
    TelegramAlreadyLinkedToAnotherUser: status.HTTP_409_CONFLICT,
    UserAlreadyHasTelegramLinked: status.HTTP_409_CONFLICT,
    # 429 Too Many Requests
    ScheduleEditTooFast: status.HTTP_429_TOO_MANY_REQUESTS,
    EmailCodeRequestTooFast: status.HTTP_429_TOO_MANY_REQUESTS,
    # Covers every subclass (OTP and login) via the exception MRO lookup.
    TooManyAttempts: status.HTTP_429_TOO_MANY_REQUESTS,
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
            code="HTTP_ERROR",
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
        content=_build_error_content(code="INTERNAL_ERROR"),
    )
