from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.auth.change_email import ChangeEmail, ChangeEmailCommand
from fanfan.application.auth.change_password import (
    ChangePassword,
    ChangePasswordCommand,
)
from fanfan.core.exceptions.auth import IncorrectPassword, UserNotAuthenticated
from fanfan.core.exceptions.users import EmailAlreadyExists, UserNotFound
from fanfan.presentation.web.schemas.error import ErrorMessage

security_router = APIRouter()


@security_router.post(
    "/password",
    status_code=status.HTTP_200_OK,
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
    data: ChangePasswordCommand,
    interactor: FromDishka[ChangePassword],
) -> None:
    try:
        await interactor(data)
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except IncorrectPassword as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=e.message
        ) from e


@security_router.post(
    "/email",
    status_code=status.HTTP_200_OK,
    summary="Change current user email",
    description="Changes the authenticated user's email address "
    "and sends a verification link to the new email.",
    responses={
        200: {"description": "Email changed and verification requested."},
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
    data: ChangeEmailCommand,
    interactor: FromDishka[ChangeEmail],
) -> None:
    try:
        await interactor(data)
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except EmailAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=e.message
        ) from e
