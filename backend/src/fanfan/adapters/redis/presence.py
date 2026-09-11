import time
from collections.abc import Awaitable
from typing import cast

from redis.asyncio import Redis

from fanfan.application.ports.presence import PresenceGateway
from fanfan.core.vo.user import UserId

# A user counts as online for this long after their last refresh. The SSE route
# refreshes presence every PRESENCE_REFRESH_INTERVAL_SECONDS (15s) while a
# connection is held, so the window is 3x that: it survives a couple of missed
# refreshes (a brief network stall) yet a genuinely dead connection ages out
# within ~45s — the same bound the frontend liveness watchdog uses to give up on
# a silent stream (HEARTBEAT_TIMEOUT_MS in events.svelte.ts).
_ONLINE_WINDOW_SECONDS = 45

# One sorted set for everyone: member = user id, score = last-seen unix time.
# A member is unique per user, so multiple tabs/devices collapse to one online
# user, and a stale score is trimmed on read instead of needing a cleanup job.
_KEY = "presence:online"


class RedisPresenceGateway(PresenceGateway):
    """Presence as a Redis sorted set of user id -> last-seen timestamp."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def mark_online(self, user_id: UserId) -> None:
        now = time.time()
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zadd(_KEY, {str(user_id): now})
            # Bound the key's own lifetime so it clears itself once the last
            # user disconnects and stops refreshing, rather than lingering with
            # only stale members no read ever trims.
            pipe.expire(_KEY, _ONLINE_WINDOW_SECONDS)
            await pipe.execute()

    async def count_online(self) -> int:
        cutoff = time.time() - _ONLINE_WINDOW_SECONDS
        async with self.redis.pipeline(transaction=True) as pipe:
            # Drop everyone whose last refresh fell outside the window, then
            # count who remains — trimming on read keeps the set bounded without
            # a separate sweep.
            pipe.zremrangebyscore(_KEY, 0, cutoff)
            pipe.zcard(_KEY)
            _, count = await cast(
                "Awaitable[tuple[int, int]]",
                pipe.execute(),
            )
        return count
