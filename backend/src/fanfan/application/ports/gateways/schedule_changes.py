from typing import Protocol

from fanfan.application.dto.page import Pagination
from fanfan.application.dto.schedule_change import ScheduleChangeFullDTO
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.schedule_change import ScheduleChangeId


class ScheduleChangeGateway(Protocol):
    async def add(self, change: ScheduleChange) -> None: ...
    async def get_by_id(self, change_id: ScheduleChangeId) -> ScheduleChange | None: ...
    async def delete(self, change: ScheduleChange) -> None: ...

    async def read_schedule_change(
        self, change_id: ScheduleChangeId
    ) -> ScheduleChangeFullDTO | None: ...

    async def read_list_schedule_changes(
        self, pagination: Pagination
    ) -> list[ScheduleChangeFullDTO]: ...

    async def read_seconds_since_last_change(self) -> float | None:
        """Seconds since the newest change was recorded, by the database clock."""
        ...
