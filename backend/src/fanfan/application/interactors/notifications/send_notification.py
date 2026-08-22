import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.notifier import (
    PushNotifierPort,
    TelegramNotifierPort,
    VkNotifierPort,
)
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    MailingNotFound,
    NotificationNotFound,
)
from fanfan.core.models.notification import Notification
from fanfan.core.vo.mailing import MailingStatus
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
            # Read the mailing without locking it. Sending is read-only towards
            # the mailing — we only gate on whether it was cancelled — and it
            # holds the transaction open across the network send (webpush / VK /
            # Telegram). Loading via get() would take SELECT ... FOR UPDATE and
            # hold that exclusive row lock across the send, so the three send
            # subscribers fanning out one mailing serialize on that row (and
            # contend with the writers that legitimately lock it) until a waiter
            # exceeds lock_timeout. A plain read observes the status instead.
            mailing = await self.mailing_gateway.read_mailing(notification.mailing_id)
            if mailing is None:
                raise MailingNotFound
            if mailing.status is MailingStatus.CANCELLED:
                raise MailingAlreadyCancelled
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
