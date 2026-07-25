from typing import Protocol

from fanfan.application.dto.subscription import SubscriptionFullDTO
from fanfan.core.models.subscription import (
    Subscription,
)
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionGateway(Protocol):
    async def add(self, subscription: Subscription) -> None: ...
    async def get_by_id(
        self, subscription_id: SubscriptionId
    ) -> Subscription | None: ...
    async def delete(self, subscription: Subscription) -> None: ...

    async def read_upcoming_subscriptions(
        self, current_event_queue: int
    ) -> list[SubscriptionFullDTO]: ...

    async def read_subscriptions_by_user(
        self, user_id: UserId
    ) -> list[SubscriptionFullDTO]: ...
