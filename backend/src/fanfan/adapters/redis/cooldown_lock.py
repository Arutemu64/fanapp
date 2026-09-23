import contextlib
from types import TracebackType

from redis.asyncio import Redis
from redis.asyncio.lock import Lock
from redis.exceptions import LockError

from fanfan.application.ports.cooldown_lock import CooldownLock, CooldownLockFactory
from fanfan.core.exceptions.rate_limit import CooldownActive, CooldownLockBusy


class RedisCooldownLock(CooldownLock):
    def __init__(
        self, redis: Redis, lock: Lock, timestamp_key: str, cooldown_period: float
    ) -> None:
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
            raise CooldownLockBusy

        now = await self._get_redis_time()
        last = await self._get_last_timestamp() or 0

        if (now - last) < self.cooldown_period:
            await self._release_lock()
            # Compute the wait from Redis time so the value matches the
            # clock that produced the stored timestamp (no app/Redis skew).
            retry_after = max(0, int(last + self.cooldown_period - now))
            raise CooldownActive(retry_after=retry_after)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            # Expire the timestamp once the cooldown is over so per-key
            # entries (e.g. per-email) do not accumulate in Redis forever.
            await self.redis.set(
                self.timestamp_key,
                await self._get_redis_time(),
                ex=int(self.cooldown_period) + 1,
            )
        await self._release_lock()


class RedisCooldownLockFactory(CooldownLockFactory):
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def __call__(
        self,
        key: str,
        *,
        cooldown_period: float = 60,
        blocking: bool = True,
        lock_timeout: float = 60,
        blocking_timeout: float | None = None,
    ) -> CooldownLock:
        # Without a blocking_timeout a blocking acquire waits forever, which
        # could hang a request indefinitely. Cap the wait at lock_timeout (the
        # longest another holder can keep the lock) so acquire always returns.
        if blocking and blocking_timeout is None:
            blocking_timeout = lock_timeout
        return RedisCooldownLock(
            redis=self.redis,
            lock=self.redis.lock(
                name=f"cooldown:{key}:lock",
                timeout=lock_timeout,
                blocking=blocking,
                blocking_timeout=blocking_timeout,
            ),
            timestamp_key=f"cooldown:{key}:timestamp",
            cooldown_period=cooldown_period,
        )
