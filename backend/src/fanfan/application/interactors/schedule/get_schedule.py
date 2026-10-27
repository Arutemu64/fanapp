import hashlib
from dataclasses import dataclass

from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEntryDTO
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)


class GetScheduleOutput(BaseModel):
    schedule: list[ScheduleEntryDTO]


@dataclass(frozen=True, slots=True)
class RenderedSchedule:
    """The serialized schedule plus a strong ETag hashed from it (ADR-0047)."""

    etag: str
    payload: str


def _compute_etag(payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f'"{digest}"'


class GetSchedule:
    def __init__(self, schedule_gateway: ScheduleEntryGateway) -> None:
        self.schedule_gateway = schedule_gateway

    async def __call__(self) -> RenderedSchedule:
        entries = await self.schedule_gateway.read_list_schedule()
        payload = GetScheduleOutput(schedule=entries).model_dump_json()
        return RenderedSchedule(etag=_compute_etag(payload), payload=payload)
