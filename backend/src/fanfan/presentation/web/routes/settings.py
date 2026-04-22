from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.dto.settings import AppSettingsDTO
from fanfan.application.interactors.settings.get_settings import GetSettings
from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
    UpdateSettings,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

settings_router = APIRouter(tags=["Settings"], prefix="/settings")


@settings_router.get(
    "",
    summary="Get festival settings",
    description="Returns the current festival settings that organizers can manage.",
    responses={
        200: {
            "model": AppSettingsDTO,
            "description": "Festival settings retrieved successfully.",
        },
        404: {
            "model": ErrorMessage,
            "description": "Festival settings were not found.",
        },
    },
)
@inject
async def get_settings(
    interactor: FromDishka[GetSettings],
) -> AppSettingsDTO:
    return await interactor()


__all__ = ["settings_router"]


@settings_router.patch(
    "",
    status_code=200,
    summary="Update festival settings",
    description="Updates festival settings that are available to organizers.",
    responses={
        200: {"description": "Festival settings updated successfully."},
        404: {
            "model": ErrorMessage,
            "description": "Festival settings were not found.",
        },
    },
)
@inject
async def update_settings(
    data: UpdateAppSettingsInput,
    interactor: FromDishka[UpdateSettings],
) -> None:
    await interactor(data)
