from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fanfan.core.vo.schedule_event import ScheduleEventId, ScheduleEventPublicNumber


@dataclass(slots=True, kw_only=True)
class ScheduleEvent:  # noqa: PLW1641
    id: ScheduleEventId
    public_number: ScheduleEventPublicNumber
    title: str
    duration: int
    order: float
    is_current: bool
    is_skipped: bool
    nomination_title: str | None
    block_title: str | None

    def __eq__(self, other: ScheduleEvent | Any) -> bool:
        return isinstance(other, ScheduleEvent) and self.id == other.id
