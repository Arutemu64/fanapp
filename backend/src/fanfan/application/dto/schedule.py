from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.schedule_event import ScheduleEventId


class ScheduleEventFullDTO(BaseModel):
    id: ScheduleEventId
    number: int
    title: str
    duration_seconds: int
    order: float
    is_current: bool
    is_skipped: bool
    nomination_title: str | None
    block_title: str | None

    # Real moment this event went on stage. Published as the anchor clients
    # measure the wait from themselves (ADR-0013); None until first set.
    actual_start_time: datetime | None = None

    # Calculated values
    queue: int | None
