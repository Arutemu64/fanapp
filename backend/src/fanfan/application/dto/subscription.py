from pydantic import BaseModel, Field

from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionEventDTO(BaseModel):
    id: ScheduleEntryId
    number: int | None
    title: str

    position: int | None


class SubscriptionFullDTO(BaseModel):
    id: SubscriptionId
    user_id: UserId = Field(exclude=True)
    lead_minutes: int
    reminded_by_change_id: ScheduleChangeId | None = Field(default=None, exclude=True)
    event: SubscriptionEventDTO
