from datetime import UTC, datetime

from pydantic import BaseModel, Field

from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.vo.notification import NotificationId


class MarkNotificationsReadInput(BaseModel):
    notification_ids: list[NotificationId] = Field(max_length=500)


class MarkNotificationsRead:
    def __init__(
        self,
        notifications_gateway: NotificationGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ) -> None:
        self.notifications_gateway = notifications_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: MarkNotificationsReadInput) -> None:
        if not data.notification_ids:
            return
        current_user_id = await self.current_user_provider.require_user_id()
        timestamp = datetime.now(UTC)
        await self.notifications_gateway.mark_read_for_user(
            user_id=current_user_id,
            notification_ids=data.notification_ids,
            timestamp=timestamp,
        )
        await self.uow.commit()
