import logging
from collections.abc import AsyncIterable

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from fanfan.application.interactors.sse.stream_events import StreamEvents

sse_router = APIRouter(tags=["SSE"])
logger = logging.getLogger(__name__)


@sse_router.get(
    "/events",
    summary="Stream events via SSE",
    description=(
        "Opens a Server-Sent Events connection to receive real-time event updates."
    ),
    response_class=EventSourceResponse,
    responses={
        200: {"description": "SSE stream established. Returns text/event-stream."},
    },
)
@inject
async def stream_events(
    interactor: FromDishka[StreamEvents],
) -> AsyncIterable[ServerSentEvent]:
    # Native FastAPI SSE: routing layer handles encoding, keepalive pings and
    # client-disconnect detection, so the generator only maps domain messages.
    async for message in interactor():
        if message.data is None:
            # Empty data line, matching the prior wire format.
            yield ServerSentEvent(event=message.event_name, raw_data="")
        else:
            # dict payloads are JSON-serialized by the router.
            yield ServerSentEvent(event=message.event_name, data=message.data)
