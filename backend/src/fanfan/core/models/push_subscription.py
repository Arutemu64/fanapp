from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.push_subscription import PushSubscriptionId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class PushSubscription(AggregateRoot):
    id: PushSubscriptionId
    user_id: UserId
    endpoint: str
    p256dh: str
    auth: str
