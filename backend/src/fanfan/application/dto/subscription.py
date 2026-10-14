from pydantic import BaseModel

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
    counter: int
    event: SubscriptionEventDTO
