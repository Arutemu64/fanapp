from typing import Protocol

from fanfan.application.dto.schedule_change import ScheduleChangeFullDTO
from fanfan.core.vo.schedule_change import ScheduleChangeId


class ScheduleChangeQuery(Protocol):
    async def read_schedule_change(
        self, change_id: ScheduleChangeId
    ) -> ScheduleChangeFullDTO | None: ...

    async def read_list_schedule_changes(self) -> list[ScheduleChangeFullDTO]: ...
