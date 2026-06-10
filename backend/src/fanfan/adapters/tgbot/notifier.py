import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

from fanfan.application.ports.gateways.social_ids import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.notifier import Notifier
from fanfan.core.exceptions.notifications import (
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    def __init__(
        self,
        bot: Bot,
        user_gateway: UserGateway,
        social_id_gateway: SocialIdentityGateway,
    ) -> None:
        self.social_id_gateway = social_id_gateway
        self.bot = bot
        self.user_gateway = user_gateway

    @staticmethod
    def _render_message_text(notification: Notification) -> str:
        return f"<b>{notification.title.upper()}</b>\n\n{notification.body}"

    async def send_notification(self, notification: Notification) -> None:
        user = await self.user_gateway.get_by_id(notification.user_id)
        if user is None or not user.settings.receive_telegram_notifications:
            raise UserNotReachable

        social_id = await self.social_id_gateway.get_by_provider(
            user_id=notification.user_id, provider="telegram"
        )
        if social_id is None:
            raise UserNotReachable
        try:
            await self.bot.send_message(
                chat_id=int(social_id.provider_id),
                text=self._render_message_text(notification),
                # TODO Add markup?
            )
        except TelegramRetryAfter as e:
            raise NotificationRetryAfter(retry_after=e.retry_after) from e
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            raise UserNotReachable from e
        return
