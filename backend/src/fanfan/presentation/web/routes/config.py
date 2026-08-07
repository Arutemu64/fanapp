from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.dto.settings import PublicConfigDTO
from fanfan.application.interactors.settings.get_public_config import GetPublicConfig

# Public, unauthenticated: the home page reads this before login and on a cold
# or offline PWA load. No session_security marker, mirroring schedule/public.
config_router = APIRouter(tags=["Config"], prefix="/config")


@config_router.get(
    "",
    summary="Get public config",
    description="Returns the public festival config the SPA needs before login.",
    responses={
        200: {
            "model": PublicConfigDTO,
            "description": "Public config retrieved successfully.",
        },
    },
)
@inject
async def get_public_config(
    interactor: FromDishka[GetPublicConfig],
) -> PublicConfigDTO:
    return await interactor()


__all__ = ["config_router"]
