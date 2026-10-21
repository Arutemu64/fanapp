import asyncio
from collections.abc import AsyncIterator

import pytest
from adaptix import Retort
from dishka import AsyncContainer
from redis.asyncio import Redis

from fanfan.adapters.redis.realtime_gateway import RedisRealtimeGateway
from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.core.vo.user import generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

# Long enough for a real Redis round trip, short enough to keep a failure quick.
_RECEIVE_TIMEOUT_SECONDS = 2.0
# A message that must NOT arrive is given this long to show up anyway.
_SILENCE_SECONDS = 0.3


@pytest.fixture
async def gateway(
    dishka_request: AsyncContainer,
) -> AsyncIterator[RedisRealtimeGateway]:
    redis = await dishka_request.get(Redis)
    retort = await dishka_request.get(Retort)
    realtime = RedisRealtimeGateway(redis, retort)
    yield realtime
    await realtime.close()


async def _next(stream: AsyncIterator[SSEMessage]) -> SSEMessage:
    return await asyncio.wait_for(anext(stream), _RECEIVE_TIMEOUT_SECONDS)


async def test_broadcast_reaches_every_stream(gateway: RedisRealtimeGateway) -> None:
    anonymous = gateway.subscribe(None)
    signed_in = gateway.subscribe(generate_user_id())
    pending = [asyncio.ensure_future(_next(s)) for s in (anonymous, signed_in)]
    await asyncio.sleep(_SILENCE_SECONDS)

    message = SSEMessage(SSEEventName.SCHEDULE_UPDATED)
    await gateway.publish(message)

    assert await asyncio.gather(*pending) == [message, message]


async def test_user_message_reaches_only_that_user(
    gateway: RedisRealtimeGateway,
) -> None:
    user_id = generate_user_id()
    mine = asyncio.ensure_future(_next(gateway.subscribe(user_id)))
    other = asyncio.ensure_future(_next(gateway.subscribe(generate_user_id())))
    await asyncio.sleep(_SILENCE_SECONDS)

    message = SSEMessage(
        SSEEventName.NOTIFICATION_CREATED, data={"title": "Личное сообщение"}
    )
    await gateway.publish(message, user_id=user_id)

    assert await mine == message
    await asyncio.sleep(_SILENCE_SECONDS)
    assert not other.done()
    other.cancel()
