import logging

from pydantic import BaseModel

from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.adapters.db.gateways.notifications import NotificationGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.notifications.push import PushNotifier
from fanfan.adapters.notifications.telegram import TelegramNotifier
from fanfan.core.exceptions.notifications import NotificationNotFound
from fanfan.core.models.notification import Notification
from fanfan.core.services.notifications import NotificationService
from fanfan.core.vo.notification import NotificationId

logger = logging.getLogger(__name__)


class SendNotificationCommand(BaseModel):
    notification_id: NotificationId


class SendNotification:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        notifications_service: NotificationService,
        user_gateway: UserGateway,
        tg_notifier: TelegramNotifier,
        push_notifier: PushNotifier,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.notifications_service = notifications_service
        self.user_gateway = user_gateway
        self.tg_notifier = tg_notifier
        self.push_notifier = push_notifier
        self.uow = uow

    async def _get_notification(self, data: SendNotificationCommand) -> Notification:
        notification = await self.notification_gateway.get_notification(
            data.notification_id
        )
        if notification is None:
            raise NotificationNotFound
        await self.notifications_service.ensure_active_mailing(notification.mailing_id)
        return notification

    async def send_notification_to_telegram(
        self, data: SendNotificationCommand
    ) -> None:
        notification = await self._get_notification(data)
        await self.tg_notifier.send_notification(notification)

    async def send_notification_to_push(self, data: SendNotificationCommand) -> None:
        notification = await self._get_notification(data)
        await self.push_notifier.send_notification(notification)
