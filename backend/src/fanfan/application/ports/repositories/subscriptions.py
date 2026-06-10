from typing import Protocol

from fanfan.application.dto.subscription import SubscriptionFullDTO
from fanfan.core.models.subscription import (
    Subscription,
)
from fanfan.core.vo.subscription import SubscriptionId


class SubscriptionRepository(Protocol):
    async def add(self, subscription: Subscription) -> None: ...
    async def get_by_id(
        self, subscription_id: SubscriptionId
    ) -> Subscription | None: ...
    async def delete(self, subscription: Subscription) -> None: ...

    # Read projections (return DTOs, not aggregates)
    async def read_upcoming_subscriptions(
        self, current_event_queue: int
    ) -> list[SubscriptionFullDTO]: ...
