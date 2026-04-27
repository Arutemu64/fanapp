from pydantic import BaseModel

from fanfan.application.dto.schedule_change import ScheduleChangeFullDTO
from fanfan.application.ports.queries.schedule_changes import (
    ScheduleChangeQuery,
)


class ListScheduleChangesResult(BaseModel):
    schedule_changes: list[ScheduleChangeFullDTO]


class ListScheduleChanges:
    def __init__(self, schedule_change_query: ScheduleChangeQuery):
        self.schedule_change_query = schedule_change_query

    async def __call__(self) -> ListScheduleChangesResult:
        schedule_changes = await self.schedule_change_query.read_list_schedule_changes()
        return ListScheduleChangesResult(schedule_changes=schedule_changes)
