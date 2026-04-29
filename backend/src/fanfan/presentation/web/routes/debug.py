from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

debug_router = APIRouter(tags=["Debug"], prefix="/debug")


class DebugResponse(BaseModel):
    url: str
    scheme: str
    headers: dict[str, str]


class HealthCheckResponse(BaseModel):
    status: Literal["healthy"]


@debug_router.get("/")
def debug(request: Request) -> DebugResponse:
    return DebugResponse(
        url=str(request.url),
        scheme=request.url.scheme,
        headers=dict(request.headers),
    )


@debug_router.get("/health")
def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="healthy")
