from pydantic import BaseModel

from fanfan.core.vo.schedule_event import ScheduleEventId, ScheduleEventPublicNumber
from fanfan.core.vo.subscription import SubscriptionId


class ScheduleEventSubscriptionDTO(BaseModel):
    id: SubscriptionId
    counter: int


class ScheduleEventFullDTO(BaseModel):
    id: ScheduleEventId
    public_number: ScheduleEventPublicNumber
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

    # User-specific values
    user_subscription: ScheduleEventSubscriptionDTO | None
