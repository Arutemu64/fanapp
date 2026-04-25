from typing import Protocol

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.core.vo.user import UserId


class ScheduleEventQuery(Protocol):
    async def read_next_event(self) -> ScheduleEventFullDTO | None: ...

    async def read_current_event(self) -> ScheduleEventFullDTO | None: ...

    async def read_list_schedule(
        self, user_id: UserId | None
    ) -> list[ScheduleEventFullDTO]: ...
