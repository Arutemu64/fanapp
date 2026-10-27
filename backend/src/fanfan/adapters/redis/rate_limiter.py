from redis.asyncio import Redis

from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.core.exceptions.rate_limit import TooManyAttempts


class RedisRateLimiter(RateLimiter):
    """Fixed-window attempt counter backed by Redis INCR/EXPIRE."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @staticmethod
    def _counter_key(key: str) -> str:
        return f"rate_limit:counter:{key}"

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        counter_key = self._counter_key(key)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(counter_key)
            pipe.expire(counter_key, max(1, window_seconds), nx=True)
            attempts, _ = await pipe.execute()
        if attempts > limit:
            retry_after = await self.redis.ttl(counter_key)
            raise TooManyAttempts(retry_after=max(1, retry_after))

    async def reset(self, key: str) -> None:
        await self.redis.delete(self._counter_key(key))
