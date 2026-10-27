import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any, cast
from uuid import uuid4

import pytest

from fanfan.adapters.nats.factory import NATSClient
from fanfan.adapters.nats.realtime_gateway import NatsRealtimeGateway
from fanfan.adapters.serialization import create_retort
from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.core.vo.user import UserId

pytestmark = pytest.mark.asyncio

type Handler = Callable[[Any], Awaitable[None]]


class StubMsg:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.data = json.dumps(payload).encode()


class StubSubscription:
    def __init__(self, nc: StubNatsClient, subject: str) -> None:
        self.nc = nc
        self.subject = subject

    async def unsubscribe(self) -> None:
        del self.nc.handlers[self.subject]


class StubNatsClient:
    """Keeps one handler per subject and delivers messages to it directly."""

    def __init__(self) -> None:
        self.handlers: dict[str, Handler] = {}
        self.subscribe_calls: list[str] = []

    async def subscribe(self, subject: str, cb: Handler) -> StubSubscription:
        self.subscribe_calls.append(subject)
        self.handlers[subject] = cb
        return StubSubscription(self, subject)

    async def deliver(self, subject: str, message: SSEMessage) -> None:
        await self.handlers[subject](StubMsg({"event_name": message.event_name}))


def _gateway(nc: StubNatsClient) -> NatsRealtimeGateway:
    return NatsRealtimeGateway(nc=cast("NATSClient", nc), retort=create_retort())


def _subscribe(
    gateway: NatsRealtimeGateway, user_id: UserId | None = None
) -> AsyncGenerator[SSEMessage]:
    return cast("AsyncGenerator[SSEMessage]", gateway.subscribe(user_id=user_id))


async def _next(stream: AsyncGenerator[SSEMessage]) -> SSEMessage:
    return await asyncio.wait_for(anext(stream), timeout=1)


async def test_broadcast_reaches_every_stream_through_one_subscription() -> None:
    nc = StubNatsClient()
    gateway = _gateway(nc)
    first = _subscribe(gateway)
    second = _subscribe(gateway, UserId(uuid4()))

    first_pending = asyncio.ensure_future(_next(first))
    second_pending = asyncio.ensure_future(_next(second))
    await asyncio.sleep(0)
    await nc.deliver(
        "sse.broadcast.*", SSEMessage(event_name=SSEEventName.SCHEDULE_UPDATED)
    )

    assert (await first_pending).event_name == SSEEventName.SCHEDULE_UPDATED
    assert (await second_pending).event_name == SSEEventName.SCHEDULE_UPDATED
    assert nc.subscribe_calls.count("sse.broadcast.*") == 1

    await first.aclose()
    await second.aclose()


async def test_closed_stream_stops_receiving_and_drops_its_user_subscription() -> None:
    nc = StubNatsClient()
    gateway = _gateway(nc)
    user_id = UserId(uuid4())
    stream = _subscribe(gateway, user_id)
    pending = asyncio.ensure_future(_next(stream))
    await asyncio.sleep(0)
    await nc.deliver(
        f"sse.user.{user_id}.*",
        SSEMessage(event_name=SSEEventName.NOTIFICATION_CREATED),
    )
    assert (await pending).event_name == SSEEventName.NOTIFICATION_CREATED

    await stream.aclose()

    assert f"sse.user.{user_id}.*" not in nc.handlers
    assert "sse.broadcast.*" in nc.handlers
    await nc.deliver(
        "sse.broadcast.*", SSEMessage(event_name=SSEEventName.SCHEDULE_UPDATED)
    )
