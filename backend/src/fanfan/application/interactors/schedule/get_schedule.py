from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.queries.schedule_events import (
    ScheduleEventQuery,
)


class GetScheduleOutput(BaseModel):
    schedule: list[ScheduleEventFullDTO]


class GetSchedule:
    def __init__(
        self, schedule_query: ScheduleEventQuery, id_provider: IdProvider
    ) -> None:
        self.schedule_query = schedule_query
        self.id_provider = id_provider

    async def __call__(self) -> GetScheduleOutput:
        current_user_id = await self.id_provider.get_current_user_id()
        events = await self.schedule_query.read_list_schedule(user_id=current_user_id)
        return GetScheduleOutput(schedule=events)
