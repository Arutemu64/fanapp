from collections.abc import Sequence
from typing import Protocol

from fanfan.application.dto.subscription import SubscriptionFullDTO
from fanfan.core.models.subscription import (
    Subscription,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionGateway(Protocol):
    async def add(self, subscription: Subscription) -> None: ...
    async def get_by_id(
        self, subscription_id: SubscriptionId
    ) -> Subscription | None: ...
    async def delete(self, subscription: Subscription) -> None: ...

    async def set_reminded_by(
        self,
        subscription_ids: Sequence[SubscriptionId],
        change_id: ScheduleChangeId | None,
    ) -> None: ...

    async def read_subscriptions_to_notify(
        self,
        current_event_position: int,
        changed_event_id: ScheduleEntryId,
    ) -> list[SubscriptionFullDTO]:
        """Subscriptions to acts at or after the stage, plus the changed act's."""
        ...

    async def read_subscriptions_by_user(
        self, user_id: UserId
    ) -> list[SubscriptionFullDTO]: ...
