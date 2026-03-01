from dataclasses import dataclass

from fanfan.core.vo.push_subscription import PushSubscriptionId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class PushSubscription:
    id: PushSubscriptionId | None = None
    user_id: UserId
    endpoint: str
    p256dh: str
    auth: str
