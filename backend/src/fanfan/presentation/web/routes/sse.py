import logging

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from sse_starlette import EventSourceResponse

from fanfan.application.sse.stream_events import StreamEvents

sse_router = APIRouter(tags=["SSE"])
logger = logging.getLogger(__name__)


@sse_router.get(
    "/events",
    summary="Stream events via SSE",
    description=(
        "Opens a Server-Sent Events connection to receive real-time event updates."
    ),
    responses={
        200: {"description": "SSE stream established. Returns text/event-stream."},
    },
)
@inject
async def stream_events(
    request: Request,
    interactor: FromDishka[StreamEvents],
) -> EventSourceResponse:
    logger.info(
        "SSE request accepted",
        extra={"client": request.client.host if request.client else None},
    )

    async def event_generator():
        async for message in interactor():
            if await request.is_disconnected():
                logger.info(
                    "SSE request disconnected",
                    extra={"client": request.client.host if request.client else None},
                )
                break
            yield {
                "event": message.event_name,
                "data": message.data if message.data is not None else "",
            }

    # Send periodic pings so idle streams stay visibly alive through proxies.
    return EventSourceResponse(event_generator(), ping=10)
