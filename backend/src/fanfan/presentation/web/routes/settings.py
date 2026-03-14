from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.settings.get_settings import GetSettings
from fanfan.application.settings.update_settings import (
    UpdateAppSettingsCommand,
    UpdateSettings,
)
from fanfan.core.dto.settings import AppSettingsDTO
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.settings import SettingsNotFound
from fanfan.core.exceptions.users import UserNotFound
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
    try:
        # Convert the domain dataclass into an explicit response model for OpenAPI.
        return AppSettingsDTO.model_validate(await interactor())
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except AccessDenied as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
    except SettingsNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


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
    data: UpdateAppSettingsCommand,
    interactor: FromDishka[UpdateSettings],
) -> None:
    try:
        await interactor(data)
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except AccessDenied as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
    except SettingsNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e