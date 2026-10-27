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
    """Re-render the schedule cache from committed state, then send
    ``schedule_updated`` to every screen as a live update.

    Every connected client refetches the schedule the moment the live update
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
        try:
            await self._warm_cache()
        except Exception:
            logger.exception("Failed to warm the schedule cache")
            await self.uow.rollback()

        await self.realtime.publish(SSEMessage(SSEEventName.SCHEDULE_UPDATED))

    async def _warm_cache(self) -> None:
        await self.schedule_gateway.lock_for_edit()
        cached = await render_schedule(self.schedule_gateway)
        await self.schedule_cache.set(cached)
        await self.uow.commit()
