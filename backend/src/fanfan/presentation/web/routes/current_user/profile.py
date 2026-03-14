from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request
from starlette import status

from fanfan.application.current_user.get_current_user import GetCurrentUser
from fanfan.application.current_user.update_user import (
    UpdateCurrentUser,
    UpdateCurrentUserCommand,
)
from fanfan.application.current_user.update_user_settings import (
    UpdateUserSettings,
    UpdateUserSettingsCommand,
)
from fanfan.core.dto.user import CurrentUserDTO
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UsernameAlreadyTaken, UserNotFound
from fanfan.presentation.web.schemas.error import ErrorMessage

profile_router = APIRouter()


@profile_router.get(
    "/",
    summary="Get current user",
    description="Retrieves the currently authenticated user's profile information.",
    responses={
        200: {
            "model": CurrentUserDTO,
            "description": "User profile retrieved successfully.",
        },
    },
)
@inject
async def get_current_user(
    request: Request,
    interactor: FromDishka[GetCurrentUser],
) -> CurrentUserDTO:
    _ = request
    return await interactor()


@profile_router.patch(
    "/",
    summary="Update current user",
    description="Updates the currently authenticated user's profile information.",
    responses={
        200: {"description": "User updated successfully."},
        409: {"model": ErrorMessage, "description": "Username already taken."},
    },
)
@inject
async def update_current_user(
    data: UpdateCurrentUserCommand,
    interactor: FromDishka[UpdateCurrentUser],
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
    except UsernameAlreadyTaken as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=e.message
        ) from e


@profile_router.patch(
    "/settings",
    summary="Update current user settings",
    description="Updates the currently authenticated user's profile settings.",
    responses={200: {"description": "User settings updated successfully."}},
)
@inject
async def update_current_user_settings(
    data: UpdateUserSettingsCommand,
    interactor: FromDishka[UpdateUserSettings],
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
