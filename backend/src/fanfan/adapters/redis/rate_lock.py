import contextlib

from redis.asyncio import Redis
from redis.asyncio.lock import Lock
from redis.exceptions import LockError

from fanfan.application.ports.rate_lock import RateLock, RateLockFactory
from fanfan.core.exceptions.rate_limit import RateLimitCooldown, RateLimitInUse


class RedisRateLock(RateLock):
    def __init__(
        self, redis: Redis, lock: Lock, timestamp_key: str, cooldown_period: float
    ):
        self.redis = redis
        self.lock = lock
        self.timestamp_key = timestamp_key
        self.cooldown_period = cooldown_period

    async def _get_redis_time(self) -> float:
        seconds, microseconds = await self.redis.time()
        return seconds + microseconds / 1_000_000

    async def _get_last_timestamp(self) -> float | None:
        value = await self.redis.get(self.timestamp_key)
        return float(value) if value else None

    async def _release_lock(self) -> None:
        # The lock may have auto-expired if the critical section ran longer
        # than its timeout; releasing an expired lock raises, so ignore it.
        with contextlib.suppress(LockError):
            await self.lock.release()

    async def __aenter__(self) -> None:
        if not await self.lock.acquire():
            raise RateLimitInUse

        now = await self._get_redis_time()
        last = await self._get_last_timestamp() or 0

        if (now - last) < self.cooldown_period:
            await self._release_lock()
            # Compute the wait from Redis time so the value matches the
            # clock that produced the stored timestamp (no app/Redis skew).
            retry_after = max(0, int(last + self.cooldown_period - now))
            raise RateLimitCooldown(retry_after=retry_after)

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            # Expire the timestamp once the cooldown is over so per-key
            # entries (e.g. per-email) do not accumulate in Redis forever.
            await self.redis.set(
                self.timestamp_key,
                await self._get_redis_time(),
                ex=int(self.cooldown_period) + 1,
            )
        await self._release_lock()


class RedisRateLockFactory(RateLockFactory):
    def __init__(self, redis: Redis):
        self.redis = redis

    def __call__(
        self,
        limit_name: str,
        cooldown_period: float = 60,
        blocking: bool = True,
        lock_timeout: float = 60,
        blocking_timeout: float | None = None,
    ) -> RateLock:
        # Without a blocking_timeout a blocking acquire waits forever, which
        # could hang a request indefinitely. Cap the wait at lock_timeout (the
        # longest another holder can keep the lock) so acquire always returns.
        if blocking and blocking_timeout is None:
            blocking_timeout = lock_timeout
        return RedisRateLock(
            redis=self.redis,
            lock=self.redis.lock(
                name=f"rate_limit:{limit_name}:lock",
                timeout=lock_timeout,
                blocking=blocking,
                blocking_timeout=blocking_timeout,
            ),
            timestamp_key=f"rate_limit:{limit_name}:timestamp",
            cooldown_period=cooldown_period,
        )
