from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request, Response
from starlette import status

from fanfan.application.interactors.schedule.get_schedule import (
    GetSchedule,
    GetScheduleOutput,
)

public_router = APIRouter()

_ETAG_HEADERS = {
    "ETag": {
        "schema": {"type": "string"},
        "description": "Schedule version; send it back in If-None-Match.",
    },
}


def _if_none_match_hits(header: str | None, etag: str) -> bool:
    """Whether a conditional request already holds this exact schedule version.

    Clients echo the ETag back verbatim in ``If-None-Match``; the header may carry
    several comma-separated validators, so match against any of them. ``*`` matches
    any current representation (RFC 9110).
    """
    if header is None:
        return False
    candidates = [value.strip() for value in header.split(",")]
    return "*" in candidates or etag in candidates


@public_router.get(
    path="",
    summary="Get current schedule",
    description="Returns the full public schedule with an ETag for conditional "
    "revalidation.",
    response_model=None,
    responses={
        200: {
            "model": GetScheduleOutput,
            "description": "Schedule retrieved successfully.",
            "headers": _ETAG_HEADERS,
        },
        304: {
            "description": "Schedule unchanged since the client's cached version.",
            "headers": _ETAG_HEADERS,
        },
    },
)
@inject
async def get_schedule(
    request: Request,
    interactor: FromDishka[GetSchedule],
) -> Response:
    cached = await interactor()

    headers = {"ETag": cached.etag, "Cache-Control": "no-cache"}

    if _if_none_match_hits(request.headers.get("if-none-match"), cached.etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    return Response(
        content=cached.payload,
        media_type="application/json",
        headers=headers,
    )
