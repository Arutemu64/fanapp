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

# Emit a named `ping` event after this much stream silence. The routing layer's
# comment-based keepalives are invisible to the browser EventSource API, so the
# frontend liveness watchdog (HEARTBEAT_TIMEOUT_MS in
# frontend/src/lib/services/events.svelte.ts) relies on these named pings to
# detect silently dead connections. Keep this comfortably below common proxy
# idle timeouts (60s) and below the frontend watchdog timeout. 15s sits well
# inside the 30s floor of cellular NAT gateway idle timeouts that silently drop
# TCP mappings on mobile networks.
HEARTBEAT_INTERVAL_SECONDS = 15

# Refresh the connected user's presence marker at most this often. Every event
# and every idle ping is a chance to refresh, so a busy stream would otherwise
# write to Redis on every message; throttling keeps it to one write per interval
# whatever the traffic. It must stay below the presence online-window
# (_ONLINE_WINDOW_SECONDS in adapters/redis/presence.py) so a still-connected
# user never briefly ages out between refreshes.
PRESENCE_REFRESH_INTERVAL_SECONDS = HEARTBEAT_INTERVAL_SECONDS


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
    record_presence: FromDishka[RecordPresence],
) -> AsyncIterable[ServerSentEvent]:
    # Native FastAPI SSE: routing layer handles encoding and client-disconnect
    # detection, so this generator only maps domain messages plus heartbeats.
    # aclosing() propagates a client disconnect (GeneratorExit) into the inner
    # generator's cleanup instead of leaving it to the garbage collector.
    #
    # This loop is the one place that sees every tick — a real event or an idle
    # ping (<=HEARTBEAT_INTERVAL_SECONDS apart) — so it drives the presence
    # refresh: mark the user online on the first tick and at most once per
    # interval after, and it stops the moment the connection closes and this
    # loop ends, letting the marker age out.
    last_presence_refresh = 0.0
    async with contextlib.aclosing(
        _stream_with_heartbeat(interactor(), HEARTBEAT_INTERVAL_SECONDS)
    ) as stream:
        async for event in stream:
            now = time.monotonic()
            if now - last_presence_refresh >= PRESENCE_REFRESH_INTERVAL_SECONDS:
                await record_presence()
                last_presence_refresh = now
            yield event
