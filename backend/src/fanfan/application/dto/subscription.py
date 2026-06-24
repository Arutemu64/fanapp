from pydantic import BaseModel

from fanfan.core.vo.schedule_item import ScheduleItemId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionEventDTO(BaseModel):
    id: ScheduleItemId
    number: int
    title: str
    order: float

    # Calculated values
    queue: int | None
    time_until: int | None


class SubscriptionFullDTO(BaseModel):
    id: SubscriptionId
    user_id: UserId
    counter: int
    event: SubscriptionEventDTO
