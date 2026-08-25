from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from fanfan.application.ports.schedule_cache import (
    CachedSchedule,
    ScheduleCacheGateway,
)

# Safety net only: every user-facing schedule edit invalidates the entry
# explicitly, so this TTL just bounds staleness from out-of-band writes (the
# demo seeder, a direct DB change) and the rare read that repopulates the cache
# with a snapshot taken microseconds before a concurrent edit committed. An hour
# is far longer than any live-show edit gap, so it never masks a real change.
_CACHE_TTL_SECONDS = 3600

_KEY = "schedule:cache"
_ETAG_FIELD = "etag"
_PAYLOAD_FIELD = "payload"


class RedisScheduleCache(ScheduleCacheGateway):
    """Stores the rendered schedule payload and its ETag in a single Redis hash."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self) -> CachedSchedule | None:
        # redis-py's async stubs mistype hgetall() as a bare dict, so cast the
        # call to its real awaitable return type before awaiting it.
        data = await cast(
            "Awaitable[dict[str, str]]",
            self.redis.hgetall(_KEY),
        )
        if not data:
            return None
        return CachedSchedule(etag=data[_ETAG_FIELD], payload=data[_PAYLOAD_FIELD])

    async def set(self, cached: CachedSchedule) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(
                _KEY,
                mapping={_ETAG_FIELD: cached.etag, _PAYLOAD_FIELD: cached.payload},
            )
            pipe.expire(_KEY, _CACHE_TTL_SECONDS)
            await pipe.execute()

    async def invalidate(self) -> None:
        await self.redis.delete(_KEY)
