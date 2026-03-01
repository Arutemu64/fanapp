import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.application.common.notifier import Notifier
from fanfan.core.exceptions.notifications import (
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification
from fanfan.presentation.tgbot.keyboards.buttons import PULL_DOWN_DIALOG

logger = logging.getLogger(__name__)

DEFAULT_REPLY_MARKUP = InlineKeyboardBuilder(
    [[PULL_DOWN_DIALOG]],
).as_markup()


class TelegramNotifier(Notifier):
    def __init__(self, bot: Bot, user_gateway: UserGateway):
        self.bot = bot
        self.user_gateway = user_gateway

    @staticmethod
    def _render_message_text(notification: Notification) -> str:
        return f"<b>{notification.title.upper()}</b>\n\n{notification.body}"

    async def send_notification(self, notification: Notification) -> None:
        social_id = await self.user_gateway.get_user_social_id_by_provider(
            user_id=notification.user_id,
            provider="telegram",
        )
        if social_id is None:
            raise UserNotReachable
        try:
            await self.bot.send_message(
                chat_id=int(social_id.provider_id),
                text=self._render_message_text(notification),
                reply_markup=DEFAULT_REPLY_MARKUP,
            )
        except TelegramRetryAfter as e:
            raise NotificationRetryAfter(retry_after=e.retry_after) from e
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            raise UserNotReachable from e
        return
