import hashlib

from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
)
from fanfan.application.ports.schedule_cache import (
    CachedSchedule,
    ScheduleCacheGateway,
)


class GetScheduleOutput(BaseModel):
    schedule: list[ScheduleEventFullDTO]


def _compute_etag(payload: str) -> str:
    # Strong validator (no W/ prefix): the payload is byte-stable, so a matching
    # ETag guarantees byte-identical content. Quoted per RFC 9110.
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f'"{digest}"'


class GetSchedule:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        schedule_cache: ScheduleCacheGateway,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_cache = schedule_cache

    async def __call__(self) -> CachedSchedule:
        # The schedule is universal — identical for every viewer — and every
        # field is derived purely from stored columns, so the payload is stable
        # between edits and one cached entry serves everyone (ADR-0014). Mutating
        # interactors invalidate it after they commit. Subscriptions are served
        # separately by GetSubscriptions.
        cached = await self.schedule_cache.get()
        if cached is not None:
            return cached

        events = await self.schedule_gateway.read_list_schedule()
        payload = GetScheduleOutput(schedule=events).model_dump_json()
        cached = CachedSchedule(etag=_compute_etag(payload), payload=payload)
        await self.schedule_cache.set(cached)
        return cached
