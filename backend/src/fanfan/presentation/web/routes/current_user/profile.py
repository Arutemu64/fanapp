from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.dto.user import CurrentUserDTO
from fanfan.application.interactors.current_user.get_current_user import GetCurrentUser
from fanfan.application.interactors.current_user.update_current_user import (
    UpdateCurrentUser,
    UpdateCurrentUserInput,
)
from fanfan.application.interactors.current_user.update_user_settings import (
    UpdateUserSettings,
    UpdateUserSettingsInput,
)
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
    interactor: FromDishka[GetCurrentUser],
) -> CurrentUserDTO:
    return await interactor()


@profile_router.patch(
    "/",
    status_code=204,
    summary="Update current user",
    description="Updates the currently authenticated user's profile information.",
    responses={
        204: {"description": "User updated successfully."},
        409: {"model": ErrorMessage, "description": "Username already taken."},
    },
)
@inject
async def update_current_user(
    data: UpdateCurrentUserInput,
    interactor: FromDishka[UpdateCurrentUser],
) -> None:
    await interactor(data)


@profile_router.patch(
    "/settings",
    status_code=204,
    summary="Update current user settings",
    description="Updates the currently authenticated user's profile settings.",
    responses={204: {"description": "User settings updated successfully."}},
)
@inject
async def update_current_user_settings(
    data: UpdateUserSettingsInput,
    interactor: FromDishka[UpdateUserSettings],
) -> None:
    await interactor(data)
