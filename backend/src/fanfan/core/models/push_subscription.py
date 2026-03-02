from dataclasses import dataclass, field
from uuid import uuid7

from fanfan.core.vo.push_subscription import PushSubscriptionId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class PushSubscription:
    id: PushSubscriptionId = field(default_factory=uuid7)
    user_id: UserId
    endpoint: str
    p256dh: str
    auth: str
