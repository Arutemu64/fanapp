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
        # INCR and EXPIRE NX run as one MULTI/EXEC round-trip: two separate
        # calls would leave a window where a crash or dropped connection
        # between them strands the counter without a TTL, so it never
        # resets. NX sets the window only when the key has none yet, which
        # also covers a counter that lost its TTL for any other reason.
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(counter_key)
            pipe.expire(counter_key, max(1, window_seconds), nx=True)
            attempts, _ = await pipe.execute()
        if attempts > limit:
            retry_after = await self.redis.ttl(counter_key)
            raise TooManyAttempts(retry_after=max(1, retry_after))

    async def reset(self, key: str) -> None:
        await self.redis.delete(self._counter_key(key))
