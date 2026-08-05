import asyncio
import contextlib
from collections.abc import AsyncGenerator

import pytest

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.presentation.web.routes.sse import _stream_with_heartbeat

pytestmark = pytest.mark.unit

# Short enough to keep the test fast, long enough that a busy CI runner does
# not fire it between two immediate yields.
HEARTBEAT_INTERVAL = 0.05

HANDSHAKE = SSEMessage(
    event_name=SSEEventName.CONNECTION_ESTABLISHED,
    data={"connection_id": "test"},
)
SCHEDULE_UPDATED = SSEMessage(event_name=SSEEventName.SCHEDULE_UPDATED)


async def test_messages_pass_through_and_empty_data_stays_empty_object() -> None:
    async def source() -> AsyncGenerator[SSEMessage]:
        yield HANDSHAKE
        yield SCHEDULE_UPDATED

    events = [
        event async for event in _stream_with_heartbeat(source(), HEARTBEAT_INTERVAL)
    ]

    assert [event.event for event in events] == [
        SSEEventName.CONNECTION_ESTABLISHED,
        SSEEventName.SCHEDULE_UPDATED,
    ]
    # Payload-less signals carry an empty dict so EventSource does not drop the
    # event; the router serializes it to a non-empty `data: {}` line on the wire.
    assert events[1].data == {}


async def test_ping_injected_when_stream_is_idle() -> None:
    async def source() -> AsyncGenerator[SSEMessage]:
        yield HANDSHAKE
        # Stay idle long enough for at least one heartbeat, then send more.
        await asyncio.sleep(HEARTBEAT_INTERVAL * 3)
        yield SCHEDULE_UPDATED

    events = []
    async with contextlib.aclosing(
        _stream_with_heartbeat(source(), HEARTBEAT_INTERVAL)
    ) as stream:
        async for event in stream:
            events.append(event)
            if event.event == SSEEventName.SCHEDULE_UPDATED:
                break

    names = [event.event for event in events]
    assert names[0] == SSEEventName.CONNECTION_ESTABLISHED
    assert names[-1] == SSEEventName.SCHEDULE_UPDATED
    pings = [name for name in names if name == SSEEventName.PING]
    assert pings, "expected at least one ping during the idle window"
    assert events[names.index(SSEEventName.PING)].data == {}


async def test_close_runs_source_cleanup() -> None:
    cleaned_up = asyncio.Event()

    async def source() -> AsyncGenerator[SSEMessage]:
        try:
            yield HANDSHAKE
            await asyncio.sleep(3600)  # Block like a quiet NATS subscription.
        finally:
            cleaned_up.set()

    stream = _stream_with_heartbeat(source(), HEARTBEAT_INTERVAL)
    assert (await anext(stream)).event == SSEEventName.CONNECTION_ESTABLISHED

    # Simulate the client disconnecting mid-stream.
    await stream.aclose()

    assert cleaned_up.is_set(), "source generator cleanup did not run on close"


async def test_source_failure_propagates() -> None:
    async def source() -> AsyncGenerator[SSEMessage]:
        yield HANDSHAKE
        msg = "subscription broke"
        raise RuntimeError(msg)

    stream = _stream_with_heartbeat(source(), HEARTBEAT_INTERVAL)
    assert (await anext(stream)).event == SSEEventName.CONNECTION_ESTABLISHED

    with pytest.raises(RuntimeError, match="subscription broke"):
        await anext(stream)
