import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator, AsyncIterable

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.interactors.sse.stream_events import StreamEvents

sse_router = APIRouter(tags=["SSE"])
logger = logging.getLogger(__name__)

# Emit a named `ping` event after this much stream silence. The routing layer's
# comment-based keepalives are invisible to the browser EventSource API, so the
# frontend liveness watchdog (HEARTBEAT_TIMEOUT_MS in
# frontend/src/lib/services/events.svelte.ts) relies on these named pings to
# detect silently dead connections. Keep this comfortably below common proxy
# idle timeouts (60s) and below the frontend watchdog timeout. 15s sits well
# inside the 30s floor of cellular NAT gateway idle timeouts that silently drop
# TCP mappings on mobile networks.
HEARTBEAT_INTERVAL_SECONDS = 15


def _to_sse(message: SSEMessage) -> ServerSentEvent:
    # data is always a dict (empty for payload-less signals, see SSEMessage);
    # the router JSON-serializes it, so `{}` becomes a non-empty `data: {}` line.
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
        # Forward source messages into the queue; None signals the end.
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
                # Await the finished task so a source failure propagates
                # instead of the stream ending as a silent "success".
                await pump_task
                break
            yield _to_sse(message)
    finally:
        pump_task.cancel()
        # Let the source's async-generator cleanup (NATS unsubscribe) run.
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
) -> AsyncIterable[ServerSentEvent]:
    # Native FastAPI SSE: routing layer handles encoding and client-disconnect
    # detection, so this generator only maps domain messages plus heartbeats.
    # aclosing() propagates a client disconnect (GeneratorExit) into the inner
    # generator's cleanup instead of leaving it to the garbage collector.
    async with contextlib.aclosing(
        _stream_with_heartbeat(interactor(), HEARTBEAT_INTERVAL_SECONDS)
    ) as stream:
        async for event in stream:
            yield event
