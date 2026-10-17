from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, EmailStr, Field
from starlette import status

from fanfan.application.dto.captcha import CaptchaChallengeDTO
from fanfan.application.interactors.auth.get_captcha_challenge import (
    GetCaptchaChallenge,
    GetCaptchaChallengeInput,
)
from fanfan.application.interactors.auth.login_with_code import (
    LoginWithCode,
    LoginWithCodeInput,
)
from fanfan.application.interactors.auth.request_login_code import (
    RequestLoginCode,
    RequestLoginCodeInput,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.responses import RATE_LIMIT_RESPONSES
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.utils import get_client_ip


# Not RequestLoginCodeInput itself: that DTO also carries the client IP, which
# must come from the connection, never from a body the client controls.
class RequestLoginCodeBody(BaseModel):
    email: EmailStr
    # A real ALTCHA payload is well under 4 KB; capping it keeps a hostile
    # megabyte out of the parser (https://altcha.org/legal/security-advisory/).
    captcha_token: str | None = Field(default=None, max_length=4096)


login_code_router = APIRouter()


@login_code_router.get(
    "/captcha-challenge",
    summary="Get a captcha challenge",
    description=(
        "Issues a single-use ALTCHA proof-of-work challenge for the login-code "
        "request. The client solves it and sends the result as `captcha_token`. "
        "`challenge` is null when captcha is disabled; send no token then."
    ),
    responses={
        **RATE_LIMIT_RESPONSES,
        200: {"description": "A challenge, or null when captcha is disabled."},
    },
)
@inject
async def get_captcha_challenge(
    request: Request,
    interactor: FromDishka[GetCaptchaChallenge],
) -> CaptchaChallengeDTO:
    return await interactor(GetCaptchaChallengeInput(client_ip=get_client_ip(request)))


@login_code_router.post(
    "/request-login-code",
    summary="Request email login code",
    description=(
        "Sends a one-time six-digit sign-in code to the requested email "
        "address. Creates an account automatically when the email is new. "
        "The code is sent before the response returns, so a delivery failure "
        "is reported instead of being swallowed."
    ),
    responses={
        **RATE_LIMIT_RESPONSES,
        200: {"description": "The login code was sent to the email address."},
        403: {"model": ErrorMessage, "description": "Captcha verification failed."},
        502: {
            "model": ErrorMessage,
            "description": "The email could not be delivered — the mail service "
            "was unreachable or refused the message.",
        },
    },
)
@inject
async def request_login_code(
    request: Request,
    data: RequestLoginCodeBody,
    interactor: FromDishka[RequestLoginCode],
) -> None:
    await interactor(
        RequestLoginCodeInput(
            email=data.email,
            captcha_token=data.captcha_token,
            client_ip=get_client_ip(request),
        )
    )


@login_code_router.post(
    "/login-with-code",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Login with email code",
    description="Consumes a one-time email code and sets session cookie.",
    responses={
        204: {"description": "Successfully authenticated. Session cookie is set."},
        400: {
            "model": ErrorMessage,
            "description": "Email code is invalid or has already been used.",
        },
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def login_with_code(
    data: LoginWithCodeInput,
    interactor: FromDishka[LoginWithCode],
    config: FromDishka[WebConfig],
    response: Response,
) -> None:
    session_id = await interactor(data)

    set_auth_cookie(response, session_id, config)
