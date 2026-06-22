from typing import Protocol

from fanfan.application.dto.page import Pagination
from fanfan.application.dto.schedule_change import ScheduleChangeFullDTO
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.schedule_change import ScheduleChangeId


class ScheduleChangeGateway(Protocol):
    async def add(self, change: ScheduleChange) -> None: ...
    async def get_by_id(self, change_id: ScheduleChangeId) -> ScheduleChange | None: ...
    async def delete(self, change: ScheduleChange) -> None: ...

    # Read projections (return DTOs, not aggregates)
    async def read_schedule_change(
        self, change_id: ScheduleChangeId
    ) -> ScheduleChangeFullDTO | None: ...

    async def read_list_schedule_changes(
        self, pagination: Pagination
    ) -> list[ScheduleChangeFullDTO]: ...
