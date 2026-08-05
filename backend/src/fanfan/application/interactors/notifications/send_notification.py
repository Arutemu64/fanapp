import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.notifier import (
    PushNotifierPort,
    TelegramNotifierPort,
    VkNotifierPort,
)
from fanfan.core.exceptions.notifications import MailingNotFound, NotificationNotFound
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationId

logger = logging.getLogger(__name__)


class SendNotificationInput(BaseModel):
    notification_id: NotificationId


class SendNotification:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        tg_notifier: TelegramNotifierPort,
        push_notifier: PushNotifierPort,
        vk_notifier: VkNotifierPort,
    ):
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.tg_notifier = tg_notifier
        self.push_notifier = push_notifier
        self.vk_notifier = vk_notifier

    async def _get_notification(self, data: SendNotificationInput) -> Notification:
        notification = await self.notification_gateway.get(data.notification_id)
        if notification is None:
            raise NotificationNotFound
        if notification.mailing_id:
            mailing = await self.mailing_gateway.get(notification.mailing_id)
            if mailing is None:
                raise MailingNotFound
            mailing.ensure_active()
        return notification

    async def send_notification_to_telegram(self, data: SendNotificationInput) -> None:
        notification = await self._get_notification(data)
        await self.tg_notifier.send_notification(notification)

    async def send_notification_to_push(self, data: SendNotificationInput) -> None:
        notification = await self._get_notification(data)
        await self.push_notifier.send_notification(notification)

    async def send_notification_to_vk(self, data: SendNotificationInput) -> None:
        notification = await self._get_notification(data)
        await self.vk_notifier.send_notification(notification)
