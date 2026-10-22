from pydantic import BaseModel, Field

from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionEventDTO(BaseModel):
    id: ScheduleEntryId
    number: int | None
    title: str
    order: float

    # Calculated values
    position: int | None


class SubscriptionFullDTO(BaseModel):
    id: SubscriptionId
    user_id: UserId
    lead_minutes: int
    # Delivery bookkeeping for the schedule-change fan-out; kept out of the
    # API, where nothing reads it.
    reminded_by_change_id: ScheduleChangeId | None = Field(default=None, exclude=True)
    event: SubscriptionEventDTO
