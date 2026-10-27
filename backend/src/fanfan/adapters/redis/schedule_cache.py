import hashlib
import json
from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from fanfan.application.interactors.schedule.get_schedule import GetScheduleOutput
from fanfan.application.ports.schedule_cache import (
    CachedSchedule,
    ScheduleCacheGateway,
)

_CACHE_TTL_SECONDS = 3600

_PAYLOAD_SHAPE = hashlib.sha256(
    json.dumps(GetScheduleOutput.model_json_schema(), sort_keys=True).encode()
).hexdigest()[:12]
_KEY = f"schedule:cache:{_PAYLOAD_SHAPE}"
_ETAG_FIELD = "etag"
_PAYLOAD_FIELD = "payload"


class RedisScheduleCache(ScheduleCacheGateway):
    """Stores the rendered schedule payload and its ETag in a single Redis hash."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get(self) -> CachedSchedule | None:
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
