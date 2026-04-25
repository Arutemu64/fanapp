from typing import Protocol

from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.schedule_change import ScheduleChangeId


class ScheduleChangeRepository(Protocol):
    async def add(self, change: ScheduleChange) -> None: ...
    async def get_by_id(self, change_id: ScheduleChangeId) -> ScheduleChange | None: ...
    async def delete(self, change: ScheduleChange) -> None: ...
