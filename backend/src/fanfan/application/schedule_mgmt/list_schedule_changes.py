from pydantic import BaseModel

from fanfan.adapters.db.gateways.schedule_changes import ScheduleChangeGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.schedule_change import ScheduleChangeFullDTO


class ListScheduleChangesResult(BaseModel):
    schedule_changes: list[ScheduleChangeFullDTO]


class ListScheduleChanges:
    def __init__(self, repo: ScheduleChangeGateway, id_provider: IdProvider):
        self.repo = repo
        self.id_provider = id_provider

    async def __call__(self) -> ListScheduleChangesResult:
        schedule_changes = await self.repo.read_list_schedule_changes()
        return ListScheduleChangesResult(schedule_changes=schedule_changes)
