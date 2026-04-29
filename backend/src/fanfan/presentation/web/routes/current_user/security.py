from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Response

from fanfan.application.interactors.auth.change_email import (
    ChangeEmail,
    ChangeEmailInput,
)
from fanfan.application.interactors.auth.change_password import (
    ChangePassword,
    ChangePasswordInput,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ErrorMessage

security_router = APIRouter()


@security_router.post(
    "/password",
    summary="Change current user password",
    description="Changes the authenticated user's password. "
    "Requires the current password for verification when one is already set.",
    responses={
        200: {"description": "Password changed successfully."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
        404: {"model": ErrorMessage, "description": "User not found."},
        409: {"model": ErrorMessage, "description": "Current password is incorrect."},
    },
)
@inject
async def change_current_user_password(
    data: ChangePasswordInput,
    interactor: FromDishka[ChangePassword],
    response: Response,
    config: FromDishka[WebConfig],
) -> None:
    session_id = await interactor(data)
    set_auth_cookie(response, session_id, config)


@security_router.post(
    "/email",
    summary="Change current user email",
    description="Changes the authenticated user's email address "
    "and sends a confirmation code to the new email.",
    responses={
        200: {"description": "Email changed and confirmation code requested."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
        404: {"model": ErrorMessage, "description": "User not found."},
        409: {
            "model": ErrorMessage,
            "description": "Email already in use by another account.",
        },
    },
)
@inject
async def change_current_user_email(
    data: ChangeEmailInput,
    interactor: FromDishka[ChangeEmail],
) -> None:
    await interactor(data)
