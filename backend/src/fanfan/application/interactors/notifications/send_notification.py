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
    UserRevokedChannel,
)
from fanfan.core.models.notification import Notification
from fanfan.core.models.user import UserSettings
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.social_identity import SocialProvider
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
        notification = await self.notification_gateway.get(
            data.notification_id, lock=False
        )
        if notification is None:
            raise NotificationNotFound
        if notification.is_stale(datetime.now(UTC)):
            raise NotificationExpired
        if notification.type.is_replaced_by_later and (
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
        user = await self.user_gateway.get_by_id(user_id)
        if user is None:
            raise UserNotReachable
        return user.settings

    async def _end_read_transaction(self) -> None:
        await self.uow.commit()

    async def send_notification_to_telegram(self, data: SendNotificationInput) -> None:
        notification = await self._get_notification(data)
        settings = await self._get_user_settings(notification.user_id)
        if not settings.receive_telegram_notifications:
            raise UserNotReachable
        await self._end_read_transaction()
        try:
            await self.tg_notifier.send_notification(notification)
        except UserRevokedChannel:
            await self._switch_off(notification.user_id, SocialProvider.TELEGRAM)
            raise

    async def send_notification_to_push(self, data: SendNotificationInput) -> None:
        notification = await self._get_notification(data)
        await self._end_read_transaction()
        await self.push_notifier.send_notification(notification)

    async def send_notification_to_vk(self, data: SendNotificationInput) -> None:
        notification = await self._get_notification(data)
        settings = await self._get_user_settings(notification.user_id)
        if not settings.receive_vk_notifications:
            raise UserNotReachable
        await self._end_read_transaction()
        try:
            await self.vk_notifier.send_notification(notification)
        except UserRevokedChannel:
            await self._switch_off(notification.user_id, SocialProvider.VK)
            raise

    async def _switch_off(self, user_id: UserId, channel: SocialProvider) -> None:
        """Stop sending until the user turns the channel back on, which re-checks it."""
        user = await self.user_gateway.get_by_id(user_id)
        if user is None:
            return
        if channel is SocialProvider.TELEGRAM:
            user.update_settings(receive_telegram_notifications=False)
        else:
            user.update_settings(receive_vk_notifications=False)
        await self.user_gateway.save(user)
        await self.uow.commit()
        logger.info(
            "Messenger notifications switched off",
            extra={"user_id": str(user_id), "provider": channel.value},
        )
