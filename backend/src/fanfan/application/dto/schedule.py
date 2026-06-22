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

    # Calculated values
    queue: int | None
    time_until: int | None
