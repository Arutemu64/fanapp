from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleItemFullDTO
from fanfan.application.ports.gateways.schedule_items import (
    ScheduleItemGateway,
)


class GetScheduleOutput(BaseModel):
    schedule: list[ScheduleItemFullDTO]


class GetSchedule:
    def __init__(
        self,
        schedule_gateway: ScheduleItemGateway,
    ) -> None:
        self.schedule_gateway = schedule_gateway

    async def __call__(self) -> GetScheduleOutput:
        # The schedule is universal — identical for every viewer — so it carries
        # no per-user data and can be cached once on the client. Subscriptions
        # are served separately by GetSubscriptions.
        events = await self.schedule_gateway.read_list_schedule()
        return GetScheduleOutput(schedule=events)
