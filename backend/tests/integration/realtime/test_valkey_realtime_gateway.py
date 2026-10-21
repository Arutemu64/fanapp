import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from typing import cast
from uuid import uuid7

import pytest
from adaptix import Retort
from dishka import AsyncContainer
from redis.asyncio import Redis

from fanfan.adapters.redis.realtime_gateway import ValkeyRealtimeGateway
from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.core.vo.user import UserId

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

_TIMEOUT_SECONDS = 2


def _listen(stream: AsyncIterator[SSEMessage]) -> asyncio.Future[SSEMessage]:
    # A stream attaches to the gateway on its first anext(), so start it before
    # publishing anything it should see.
    return asyncio.ensure_future(anext(stream))


async def _publish_until_received(
    gateway: ValkeyRealtimeGateway,
    pending: asyncio.Future[SSEMessage],
    message: SSEMessage,
    user_id: UserId | None = None,
) -> SSEMessage:
    # The reader subscribes in the background once the first stream opens, and
    # pub/sub drops anything published before that lands; keep publishing
    # until the subscription is up instead of sleeping a guessed amount.
    async with asyncio.timeout(_TIMEOUT_SECONDS):
        while True:
            await gateway.publish(message, user_id=user_id)
            done, _ = await asyncio.wait({pending}, timeout=0.05)
            if done:
                return pending.result()


def _subscribe(
    gateway: ValkeyRealtimeGateway, user_id: UserId | None = None
) -> AsyncGenerator[SSEMessage]:
    # The port promises an iterator; the adapter's is a generator, closable.
    return cast("AsyncGenerator[SSEMessage]", gateway.subscribe(user_id))


@pytest.fixture
async def gateway(dishka: AsyncContainer) -> AsyncIterator[ValkeyRealtimeGateway]:
    gateway = ValkeyRealtimeGateway(await dishka.get(Redis), await dishka.get(Retort))
    yield gateway
    await gateway.close()


async def test_a_broadcast_reaches_every_stream(
    gateway: ValkeyRealtimeGateway,
) -> None:
    anonymous = _subscribe(gateway)
    signed_in = _subscribe(gateway, UserId(uuid7()))
    anonymous_next = _listen(anonymous)
    signed_in_next = _listen(signed_in)
    message = SSEMessage(SSEEventName.SCHEDULE_UPDATED)

    assert await _publish_until_received(gateway, anonymous_next, message) == message
    assert await asyncio.wait_for(signed_in_next, _TIMEOUT_SECONDS) == message

    await anonymous.aclose()
    await signed_in.aclose()


async def test_a_user_message_reaches_only_that_users_streams(
    gateway: ValkeyRealtimeGateway,
) -> None:
    user_id = UserId(uuid7())
    mine = _subscribe(gateway, user_id)
    other = _subscribe(gateway, UserId(uuid7()))
    mine_next = _listen(mine)
    other_next = _listen(other)
    personal = SSEMessage(SSEEventName.NOTIFICATION_CREATED, data={"id": "1"})

    received = await _publish_until_received(gateway, mine_next, personal, user_id)
    assert received == personal
    # The other user's stream skipped the personal message: the first thing it
    # sees is the broadcast sent after it.
    broadcast = SSEMessage(SSEEventName.CONFIG_UPDATED)
    await gateway.publish(broadcast)
    assert await asyncio.wait_for(other_next, _TIMEOUT_SECONDS) == broadcast

    await mine.aclose()
    await other.aclose()
