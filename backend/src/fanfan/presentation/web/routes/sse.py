import asyncio
import contextlib
import logging
import time
from collections.abc import AsyncGenerator, AsyncIterable

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.interactors.presence.record_presence import RecordPresence
from fanfan.application.interactors.sse.stream_events import StreamEvents

sse_router = APIRouter(tags=["SSE"])
logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 15

PRESENCE_REFRESH_INTERVAL_SECONDS = HEARTBEAT_INTERVAL_SECONDS


def _to_sse(message: SSEMessage) -> ServerSentEvent:
    return ServerSentEvent(event=message.event_name, data=message.data)


async def _stream_with_heartbeat(
    source: AsyncGenerator[SSEMessage],
    heartbeat_interval: float,
) -> AsyncGenerator[ServerSentEvent]:
    """Map source messages to SSE events, injecting `ping` events when idle.

    The queue indirection exists because timing out on the source directly
    (asyncio.wait_for around anext()) would cancel *inside* its generator and
    kill the NATS subscription; cancelling queue.get() is safe.
    """
    queue: asyncio.Queue[SSEMessage | None] = asyncio.Queue()

    async def pump() -> None:
        try:
            async for message in source:
                await queue.put(message)
        finally:
            queue.put_nowait(None)

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    queue.get(), timeout=heartbeat_interval
                )
            except TimeoutError:
                yield _to_sse(SSEMessage(event_name=SSEEventName.PING))
                continue
            if message is None:
                await pump_task
                break
            yield _to_sse(message)
    finally:
        pump_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump_task


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
    record_presence: FromDishka[RecordPresence],
) -> AsyncIterable[ServerSentEvent]:
    last_presence_refresh = 0.0
    async with contextlib.aclosing(
        _stream_with_heartbeat(interactor(), HEARTBEAT_INTERVAL_SECONDS)
    ) as stream:
        async for event in stream:
            now = time.monotonic()
            if now - last_presence_refresh >= PRESENCE_REFRESH_INTERVAL_SECONDS:
                try:
                    await record_presence()
                except Exception:
                    logger.exception("Failed to refresh user presence")
                last_presence_refresh = now
            yield event
