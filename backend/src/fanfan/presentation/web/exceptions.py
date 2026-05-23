from collections.abc import Mapping

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
from fanfan.core.exceptions.nominations import NominationNotFound
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.push_sub import (
    PushSubNotFound,
    PushSubscriptionAlreadyExists,
)
from fanfan.core.exceptions.rate_limit import EmailCodeRequestTooFast
from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    EventNotFound,
    OutdatedScheduleChange,
    SameEventsAreNotAllowed,
    ScheduleChangeNotFound,
    ScheduleEditTooFast,
    SkippedEventNotAllowed,
)
from fanfan.core.exceptions.settings import AppAppSettingsNotFound
from fanfan.core.exceptions.subscriptions import (
    SubscriptionAlreadyExist,
    SubscriptionNotFound,
)
from fanfan.core.exceptions.tickets import (
    TicketAlreadyUsed,
    TicketNotFound,
    UserAlreadyHasTicketLinked,
)
from fanfan.core.exceptions.users import (
    EmailAlreadyExists,
    TelegramAlreadyLinkedToAnotherUser,
    TelegramCannotBeUnlinkedWithoutEmail,
    UserAlreadyExists,
    UserAlreadyHasTelegramLinked,
    UserHasNoEmail,
    UsernameAlreadyTaken,
    UserNotFound,
)
from fanfan.core.exceptions.votes import AlreadyVotedInThisNomination, VoteNotFound
from fanfan.presentation.web.schemas.error import (
    ErrorMessage,
    ValidationErrorDetail,
    ValidationErrorResponse,
)

EXCEPTION_STATUS_MAP: dict[type[AppException], int] = {
    # 400 Bad Request
    InvalidOtpCode: status.HTTP_400_BAD_REQUEST,
    InvalidTelegramAuthPayload: status.HTTP_400_BAD_REQUEST,
    CurrentEventNotAllowed: status.HTTP_400_BAD_REQUEST,
    SameEventsAreNotAllowed: status.HTTP_400_BAD_REQUEST,
    SkippedEventNotAllowed: status.HTTP_400_BAD_REQUEST,
    # 401 Unauthorized
    UserNotAuthenticated: status.HTTP_401_UNAUTHORIZED,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    IncorrectPassword: status.HTTP_401_UNAUTHORIZED,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    # 403 Forbidden
    AccessDenied: status.HTTP_403_FORBIDDEN,
    # 404 Not Found
    UserNotFound: status.HTTP_404_NOT_FOUND,
    EventNotFound: status.HTTP_404_NOT_FOUND,
    NominationNotFound: status.HTTP_404_NOT_FOUND,
    ParticipantNotFound: status.HTTP_404_NOT_FOUND,
    PushSubNotFound: status.HTTP_404_NOT_FOUND,
    SubscriptionNotFound: status.HTTP_404_NOT_FOUND,
    TicketNotFound: status.HTTP_404_NOT_FOUND,
    VoteNotFound: status.HTTP_404_NOT_FOUND,
    ScheduleChangeNotFound: status.HTTP_404_NOT_FOUND,
    AppAppSettingsNotFound: status.HTTP_404_NOT_FOUND,
    # 409 Conflict
    UserAlreadyExists: status.HTTP_409_CONFLICT,
    UsernameAlreadyTaken: status.HTTP_409_CONFLICT,
    EmailAlreadyExists: status.HTTP_409_CONFLICT,
    OutdatedScheduleChange: status.HTTP_409_CONFLICT,
    AlreadyVotedInThisNomination: status.HTTP_409_CONFLICT,
    SubscriptionAlreadyExist: status.HTTP_409_CONFLICT,
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
}


def _resolve_status_code(exc: AppException) -> int:
    """Resolve the HTTP status code using the exception MRO."""
    for exc_type in type(exc).__mro__:
        if exc_type in EXCEPTION_STATUS_MAP:
            return EXCEPTION_STATUS_MAP[exc_type]

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


async def auth_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    _ = request

    if isinstance(exc.detail, Mapping):
        code = exc.detail.get("code")
        details = exc.detail.get("details")
        if isinstance(code, str) and isinstance(details, Mapping):
            return JSONResponse(
                status_code=exc.status_code,
                content=_build_error_content(code, details),
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
