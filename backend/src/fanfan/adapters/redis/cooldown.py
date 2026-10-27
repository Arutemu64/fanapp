import math
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import override

from redis.asyncio import Redis

from fanfan.application.ports.cooldown import Cooldown
from fanfan.core.exceptions.rate_limit import CooldownActive


class RedisCooldown(Cooldown):
    """One ``SET NX EX`` key per window; its TTL is the remaining cooldown.

    No lock and no stored timestamp: the atomic SET both serializes callers and
    starts the window, and the server's own TTL answers "how long to wait", so
    no app or server clock is ever read.
    """

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @staticmethod
    def _redis_key(key: str) -> str:
        return f"cooldown:{key}"

    async def _retry_after(self, redis_key: str) -> int:
        milliseconds = await self.redis.pttl(redis_key)
        return max(1, math.ceil(milliseconds / 1000))

    @override
    @asynccontextmanager
    async def claim(self, key: str, seconds: int) -> AsyncIterator[None]:
        redis_key = self._redis_key(key)
        token = secrets.token_hex(16)
        if not await self.redis.set(redis_key, token, nx=True, ex=seconds):
            raise CooldownActive(retry_after=await self._retry_after(redis_key))
        try:
            yield
        except BaseException:
            await self.redis.execute_command("DELIFEQ", redis_key, token)
            raise
