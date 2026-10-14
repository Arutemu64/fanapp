import logging

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.interactors.schedule.get_schedule import render_schedule
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.schedule_cache import ScheduleCacheGateway
from fanfan.application.ports.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PublishScheduleUpdated:
    """Re-render the schedule cache from committed state, then broadcast
    ``schedule_updated``.

    Every connected client refetches the schedule the moment the broadcast
    lands. Into an empty cache that burst is a stampede: each request misses and
    runs the schedule query before the first one can repopulate it. Warming
    first means the burst only reads Redis.
    """

    def __init__(
        self,
        schedule_gateway: ScheduleEntryGateway,
        schedule_cache: ScheduleCacheGateway,
        uow: UnitOfWork,
        realtime: RealtimeGateway,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_cache = schedule_cache
        self.uow = uow
        self.realtime = realtime

    async def __call__(self) -> None:
        # Warming is an optimisation: when it fails, the cache is still empty
        # (edits invalidate after commit), so clients refetch correct data, just
        # slower. That must not hold back the broadcast.
        try:
            await self._warm_cache()
        except Exception:
            logger.exception("Failed to warm the schedule cache")
            await self.uow.rollback()

        await self.realtime.publish(SSEMessage(SSEEventName.SCHEDULE_UPDATED))

    async def _warm_cache(self) -> None:
        # Read and store under the schedule edit lock. Unlocked, an edit could
        # commit and invalidate between our read and our write, leaving its
        # pre-edit snapshot cached until the TTL lapses. Under the lock, an edit
        # either commits before the read or invalidates after the write.
        await self.schedule_gateway.lock_for_edit()
        cached = await render_schedule(self.schedule_gateway)
        await self.schedule_cache.set(cached)
        # Ends the read-only transaction, releasing the transaction-level lock.
        await self.uow.commit()
