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

    # Calculated value: dense 1..N position among non-skipped events (ADR-0008).
    # Every field on this DTO is now derived purely from stored columns, so the
    # whole schedule read is stable between edits and cacheable (see ADR-0014).
    queue: int | None
