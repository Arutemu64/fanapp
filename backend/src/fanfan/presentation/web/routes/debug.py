from typing import Literal

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from fanfan.adapters.debug.config import DebugConfig

debug_router = APIRouter(tags=["Debug"], prefix="/debug")


class DebugResponse(BaseModel):
    url: str
    scheme: str
    headers: dict[str, str]


class HealthCheckResponse(BaseModel):
    status: Literal["healthy"]


@debug_router.get("/")
@inject
async def debug(request: Request, config: FromDishka[DebugConfig]) -> DebugResponse:
    # Echoes request headers (incl. cookies and proxy internals), so keep it to
    # debug builds. In production it must be indistinguishable from a missing route.
    if not config.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return DebugResponse(
        url=str(request.url),
        scheme=request.url.scheme,
        headers=dict(request.headers),
    )


@debug_router.get("/health")
def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="healthy")
