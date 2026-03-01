from pydantic import BaseModel

from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.adapters.db.gateways.notifications import NotificationGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.dto.notification import NewNotificationDTO
from fanfan.core.models.notification import Notification
from fanfan.core.services.notifications import NotificationService
from fanfan.core.vo.notification import NotificationId


class NewNotificationCommand(BaseModel):
    notification: NewNotificationDTO


class NewNotification:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        notifications_service: NotificationService,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.notifications_service = notifications_service
        self.uow = uow

    @staticmethod
    def _dto_to_model(notification: NewNotificationDTO) -> Notification:
        return Notification(
            id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            body=notification.body,
            type=notification.type,
            mailing_id=notification.mailing_id,
            seen_at=None,
        )

    async def __call__(self, data: NewNotificationCommand) -> NotificationId:
        async with self.uow:
            await self.notifications_service.ensure_active_mailing(
                data.notification.mailing_id
            )
            notification = self._dto_to_model(data.notification)
            await self.notification_gateway.add_notification(notification)
            await self.uow.commit()

        return notification.id
