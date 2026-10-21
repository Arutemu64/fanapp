import logging
from datetime import UTC, datetime

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.notifier import (
    PushNotifierPort,
    TelegramNotifierPort,
    VkNotifierPort,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    MailingNotFound,
    NotificationExpired,
    NotificationNotFound,
    NotificationSuperseded,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification
from fanfan.core.models.user import UserSettings
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)


class SendNotificationInput(BaseModel):
    notification_id: NotificationId


class SendNotification:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        user_gateway: UserGateway,
        tg_notifier: TelegramNotifierPort,
        push_notifier: PushNotifierPort,
        vk_notifier: VkNotifierPort,
        uow: UnitOfWork,
    ) -> None:
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.user_gateway = user_gateway
        self.tg_notifier = tg_notifier
        self.push_notifier = push_notifier
        self.vk_notifier = vk_notifier
        self.uow = uow

    async def _get_notification(self, data: SendNotificationInput) -> Notification:
        # Unlocked: nothing here is written back, and the cancellation check
        # cannot hold past the commit before the send anyway. Locking the
        # mailing row would queue every channel's send of a mailing behind the
        # fan-out storing it, and behind each other.
        notification = await self.notification_gateway.get(
            data.notification_id, lock=False
        )
        if notification is None:
            raise NotificationNotFound
        if notification.is_stale(datetime.now(UTC)):
            raise NotificationExpired
        # The senders run in parallel, so an older schedule notification can
        # reach a channel after a newer one; sent then, it would be the one left
        # on screen (push replaces by tag). Only schedule news ages this way.
        if notification.type.is_schedule and (
            await self.notification_gateway.is_superseded(notification)
        ):
            raise NotificationSuperseded
        if notification.mailing_id:
            mailing = await self.mailing_gateway.get(
                notification.mailing_id, lock=False
            )
            if mailing is None:
                raise MailingNotFound
            mailing.ensure_active()
        return notification

    async def _get_user_settings(self, user_id: UserId) -> UserSettings:
        # Whether a user wants a given channel is application policy, so the
        # decision lives here rather than in each delivery adapter (the adapters
        # only judge physical reachability). A missing user is unreachable — the
        # notification outlived its owner.
        user = await self.user_gateway.get_by_id(user_id)
        if user is None:
            raise UserNotReachable
        return user.settings

    async def _end_read_transaction(self) -> None:
        # Nothing here writes, so end the transaction before the external send.
        # A Telegram or VK call can take up to ~60s; an open transaction holds
        # its pooled connection that long, and the consumers send in parallel
        # from a small pool. The user row is read FOR UPDATE and would block
        # settings edits the same way.
        await self.uow.commit()

    async def send_notification_to_telegram(self, data: SendNotificationInput) -> None:
        notification = await self._get_notification(data)
        settings = await self._get_user_settings(notification.user_id)
        if not settings.receive_telegram_notifications:
            raise UserNotReachable
        await self._end_read_transaction()
        await self.tg_notifier.send_notification(notification)

    async def send_notification_to_push(self, data: SendNotificationInput) -> None:
        # Push has no per-channel opt-out: a live push subscription is itself the
        # user's opt-in, so there is no setting to check here.
        notification = await self._get_notification(data)
        await self._end_read_transaction()
        await self.push_notifier.send_notification(notification)

    async def send_notification_to_vk(self, data: SendNotificationInput) -> None:
        notification = await self._get_notification(data)
        settings = await self._get_user_settings(notification.user_id)
        if not settings.receive_vk_notifications:
            raise UserNotReachable
        await self._end_read_transaction()
        await self.vk_notifier.send_notification(notification)
