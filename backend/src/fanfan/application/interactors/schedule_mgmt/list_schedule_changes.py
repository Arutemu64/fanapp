from pydantic import BaseModel

from fanfan.application.dto.schedule_change import ScheduleChangeFullDTO
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.schedule_changes import (
    ScheduleChangeRepository,
)


class ListScheduleChangesResult(BaseModel):
    schedule_changes: list[ScheduleChangeFullDTO]


class ListScheduleChanges:
    def __init__(self, repo: ScheduleChangeRepository, id_provider: IdProvider):
        self.repo = repo
        self.id_provider = id_provider

    async def __call__(self) -> ListScheduleChangesResult:
        schedule_changes = await self.repo.read_list_schedule_changes()
        return ListScheduleChangesResult(schedule_changes=schedule_changes)
