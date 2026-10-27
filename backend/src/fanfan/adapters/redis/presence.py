import time
from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from fanfan.application.ports.presence import PresenceGateway
from fanfan.core.vo.user import UserId

_ONLINE_WINDOW_SECONDS = 45

_KEY = "presence:online"


class RedisPresenceGateway(PresenceGateway):
    """Presence as a Redis sorted set of user id -> last-seen timestamp."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def mark_online(self, user_id: UserId) -> None:
        now = time.time()
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zadd(_KEY, {str(user_id): now})
            pipe.expire(_KEY, _ONLINE_WINDOW_SECONDS)
            await pipe.execute()

    async def count_online(self) -> int:
        cutoff = time.time() - _ONLINE_WINDOW_SECONDS
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(_KEY, 0, cutoff)
            pipe.zcard(_KEY)
            _, count = await cast(
                "Awaitable[tuple[int, int]]",
                pipe.execute(),
            )
        return count
