from datetime import UTC, datetime

from pydantic import BaseModel

from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.vo.notification import NotificationId


class MarkNotificationsReadInput(BaseModel):
    notification_ids: list[NotificationId]


class MarkNotificationsRead:
    def __init__(
        self,
        notifications_gateway: NotificationGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ):
        self.notifications_gateway = notifications_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: MarkNotificationsReadInput) -> None:
        if not data.notification_ids:
            return
        current_user_id = await self.current_user_provider.require_user_id()
        # seen_at is a timestamptz column, so the stored instant is identical
        # regardless of tzinfo; use UTC to match every other interactor.
        timestamp = datetime.now(UTC)
        # The gateway scopes the update to current_user_id, so a caller cannot
        # mark another user's notifications read by guessing their ids.
        await self.notifications_gateway.mark_read_for_user(
            user_id=current_user_id,
            notification_ids=data.notification_ids,
            timestamp=timestamp,
        )
        await self.uow.commit()
