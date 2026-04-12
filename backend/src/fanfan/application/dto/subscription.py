from pydantic import BaseModel, ConfigDict

from fanfan.core.vo.schedule_event import ScheduleEventId, ScheduleEventPublicNumber
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionEventDTO(BaseModel):
    id: ScheduleEventId
    public_number: ScheduleEventPublicNumber
    title: str
    order: float

    # Calculated values
    queue: int | None
    time_until: int | None


class SubscriptionFullDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: SubscriptionId
    user_id: UserId
    counter: int
    event: SubscriptionEventDTO
