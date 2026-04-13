from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Response
from starlette import status

from fanfan.application.interactors.auth.login_magic_link import (
    LoginMagicLink,
    LoginMagicLinkInput,
)
from fanfan.application.interactors.auth.request_magic_link import (
    RequestMagicLink,
    RequestMagicLinkInput,
)
from fanfan.core.exceptions.auth import InvalidToken, TokenExpired
from fanfan.core.exceptions.users import UserNotFound
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ErrorMessage

magic_link_router = APIRouter()


@magic_link_router.post(
    "/request-magic-link",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request email magic link",
    description="Sends a one-time sign-in link to the requested email address. "
    "Creates an account automatically when the email is new.",
    responses={
        202: {"description": "If the email is valid, the magic link was queued."},
    },
)
@inject
async def request_magic_link(
    data: RequestMagicLinkInput,
    interactor: FromDishka[RequestMagicLink],
) -> None:
    await interactor(data)


@magic_link_router.post(
    "/login-magic-link",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Login with email magic link",
    description="Consumes a one-time email magic link token and sets session cookie.",
    responses={
        204: {"description": "Successfully authenticated. Session cookie is set."},
        400: {
            "model": ErrorMessage,
            "description": "Magic link is invalid or has already been used.",
        },
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def login_magic_link(
    data: LoginMagicLinkInput,
    interactor: FromDishka[LoginMagicLink],
    config: FromDishka[WebConfig],
    response: Response,
) -> None:
    try:
        session_id = await interactor(data)
    except (InvalidToken, TokenExpired) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e

    set_auth_cookie(response, session_id, config)
