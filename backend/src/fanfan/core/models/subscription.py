from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Subscription(AggregateRoot):
    id: SubscriptionId
    user_id: UserId
    event_id: ScheduleEntryId
    counter: int
