from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Response
from starlette import status

from fanfan.application.interactors.auth.login_with_code import (
    LoginWithCode,
    LoginWithCodeInput,
)
from fanfan.application.interactors.auth.request_login_code import (
    RequestLoginCode,
    RequestLoginCodeInput,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ErrorMessage

login_code_router = APIRouter()


@login_code_router.post(
    "/request-login-code",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request email login code",
    description="Sends a one-time six-digit sign-in code to the requested email address. "
    "Creates an account automatically when the email is new.",
    responses={
        202: {"description": "If the email is valid, the login code was queued."},
    },
)
@inject
async def request_login_code(
    data: RequestLoginCodeInput,
    interactor: FromDishka[RequestLoginCode],
) -> None:
    await interactor(data)


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
