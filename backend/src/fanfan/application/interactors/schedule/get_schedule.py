from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.ports.repositories.schedule_events import (
    ScheduleEventRepository,
)
from fanfan.application.services.current_user import CurrentUserProvider


class GetScheduleOutput(BaseModel):
    schedule: list[ScheduleEventFullDTO]


class GetSchedule:
    def __init__(
        self,
        schedule_query: ScheduleEventRepository,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.schedule_query = schedule_query
        self.current_user_provider = current_user_provider

    async def __call__(self) -> GetScheduleOutput:
        current_user_id = await self.current_user_provider.get_user_id()
        events = await self.schedule_query.read_list_schedule(user_id=current_user_id)
        return GetScheduleOutput(schedule=events)
