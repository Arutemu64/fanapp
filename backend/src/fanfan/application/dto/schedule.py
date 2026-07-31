from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.schedule_event import ScheduleEventId


class ScheduleEventFullDTO(BaseModel):
    id: ScheduleEventId
    # None for events with no public number (breaks and other filler rows).
    number: int | None
    title: str
    # Seconds; the API exposes it unconverted so clients can render sub-minute
    # acts exactly instead of rounding to whole minutes.
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
    # Absolute drift-aware predicted start, filled by the schedule timing service
    # (ADR-0008). None for past/skipped events and when nothing is on stage yet.
    expected_start_time: datetime | None = None
