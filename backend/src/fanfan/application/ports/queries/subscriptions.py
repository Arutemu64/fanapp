from typing import Protocol

from fanfan.application.dto.subscription import SubscriptionFullDTO


class SubscriptionQuery(Protocol):
    async def read_upcoming_subscriptions(
        self, current_event_queue: int
    ) -> list[SubscriptionFullDTO]: ...
