import hashlib

from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEntryDTO
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.ports.schedule_cache import (
    CachedSchedule,
    ScheduleCacheGateway,
)


class GetScheduleOutput(BaseModel):
    schedule: list[ScheduleEntryDTO]


def _compute_etag(payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f'"{digest}"'


async def render_schedule(schedule_gateway: ScheduleEntryGateway) -> CachedSchedule:
    entries = await schedule_gateway.read_list_schedule()
    payload = GetScheduleOutput(schedule=entries).model_dump_json()
    return CachedSchedule(etag=_compute_etag(payload), payload=payload)


class GetSchedule:
    def __init__(
        self,
        schedule_gateway: ScheduleEntryGateway,
        schedule_cache: ScheduleCacheGateway,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_cache = schedule_cache

    async def __call__(self) -> CachedSchedule:
        cached = await self.schedule_cache.get()
        if cached is not None:
            return cached

        cached = await render_schedule(self.schedule_gateway)
        await self.schedule_cache.set(cached)
        return cached
