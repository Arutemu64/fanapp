from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.schedule_event import ScheduleEventId


class ScheduleEventFullDTO(BaseModel):
    id: ScheduleEventId
    number: int
    title: str
    duration: int
    order: float
    is_current: bool
    is_skipped: bool
    nomination_title: str | None
    block_title: str | None

    # Real moment this event went on stage; the anchor for the projection below.
    actual_start_time: datetime | None = None

    # Calculated values
    queue: int | None
    time_until: int | None
    # Absolute drift-aware predicted start, filled by the schedule timing service
    # (ADR-0008). None for past/skipped events and when nothing is on stage yet.
    expected_start_time: datetime | None = None
