from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Header

from fanfan.application.dto.settings import AppSettingsDTO
from fanfan.application.interactors.settings.get_settings import GetSettings
from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
    UpdateSettings,
)
from fanfan.presentation.web.preconditions import parse_if_match
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ProblemDetails
from fanfan.presentation.web.security import session_security

settings_router = APIRouter(
    tags=["Settings"],
    prefix="/settings",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@settings_router.get(
    "",
    summary="Get festival settings",
    description="Returns the current festival settings that organizers can manage, "
    "with the `etag` to send back in If-Match when saving them.",
    responses={
        200: {"description": "Festival settings retrieved successfully."},
        404: {
            "model": ProblemDetails,
            "description": "Festival settings were not found.",
        },
    },
)
@inject
async def get_settings(
    interactor: FromDishka[GetSettings],
) -> AppSettingsDTO:
    return await interactor()


@settings_router.patch(
    "",
    summary="Update festival settings",
    description="Updates festival settings that are available to organizers; an "
    "omitted field is left as is and null is rejected. Returns the saved settings.",
    responses={
        200: {"description": "Festival settings updated successfully."},
        404: {
            "model": ProblemDetails,
            "description": "Festival settings were not found.",
        },
        412: {
            "model": ProblemDetails,
            "description": "Someone saved the settings after the If-Match version "
            "was read; reload and edit again.",
        },
    },
)
@inject
async def update_settings(
    data: UpdateAppSettingsInput,
    # Required rather than answered with 428 Precondition Required (RFC 6585 §3):
    # declaring it in the spec makes the generated client refuse to compile a
    # save that forgets it, which a runtime 428 would only catch in the field.
    if_match: Annotated[
        str,
        Header(description="The `etag` from GET /settings, or `*` to save regardless."),
    ],
    interactor: FromDishka[UpdateSettings],
) -> AppSettingsDTO:
    return await interactor(data, if_match=parse_if_match(if_match))


__all__ = ["settings_router"]
