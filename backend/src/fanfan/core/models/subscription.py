from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.schedule_item import ScheduleItemId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Subscription(AggregateRoot):
    id: SubscriptionId
    user_id: UserId
    schedule_item_id: ScheduleItemId
    counter: int
