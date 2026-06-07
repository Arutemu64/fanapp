from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.core.exceptions.rate_limit import TooManyAttempts


class RedisRateLimiter(RateLimiter):
    """Fixed-window attempt counter backed by Redis INCR/EXPIRE."""

    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def _counter_key(key: str) -> str:
        return f"rate_limit:counter:{key}"

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        counter_key = self._counter_key(key)
        # redis-py's async stubs mistype incr() as a plain int, so cast the
        # call to its real awaitable return type before awaiting it.
        attempts = await cast("Awaitable[int]", self.redis.incr(counter_key))
        # Start the window on the first hit so the counter eventually expires
        # instead of living forever once the key goes quiet.
        if attempts == 1:
            await self.redis.expire(counter_key, max(1, window_seconds))
        if attempts > limit:
            retry_after = await self.redis.ttl(counter_key)
            raise TooManyAttempts(retry_after=max(1, retry_after))

    async def reset(self, key: str) -> None:
        await self.redis.delete(self._counter_key(key))
