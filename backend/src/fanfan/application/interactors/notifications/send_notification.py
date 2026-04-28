import logging

from pydantic import BaseModel

from fanfan.adapters.push.push import PushNotifier
from fanfan.adapters.tgbot.notifier import TelegramNotifier
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.repositories.notifications import NotificationRepository
from fanfan.core.exceptions.notifications import MailingNotFound, NotificationNotFound
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationId

logger = logging.getLogger(__name__)


class SendNotificationInput(BaseModel):
    notification_id: NotificationId


class SendNotification:
    def __init__(
        self,
        mailing_repo: MailingRepository,
        notification_repo: NotificationRepository,
        tg_notifier: TelegramNotifier,
        push_notifier: PushNotifier,
    ):
        self.mailing_repo = mailing_repo
        self.notification_repo = notification_repo
        self.tg_notifier = tg_notifier
        self.push_notifier = push_notifier

    async def _get_notification(self, data: SendNotificationInput) -> Notification:
        notification = await self.notification_repo.get(data.notification_id)
        if notification is None:
            raise NotificationNotFound
        if notification.mailing_id:
            mailing = await self.mailing_repo.get(notification.mailing_id)
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
