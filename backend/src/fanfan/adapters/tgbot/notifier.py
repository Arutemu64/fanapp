import logging

from aiogram import Bot, html
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
    TelegramUnauthorizedError,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.notifier import Notifier
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.config import WebConfig

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    def __init__(
        self,
        bot: Bot,
        user_gateway: UserGateway,
        social_identity_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        web_config: WebConfig,
    ) -> None:
        self.social_identity_gateway = social_identity_gateway
        self.bot = bot
        self.user_gateway = user_gateway
        self.uow = uow
        self.web_config = web_config

    @staticmethod
    def _render_message_text(notification: Notification) -> str:
        # The body is already stored as a safe Telegram-compatible HTML subset
        # (see HtmlSanitizer). The title is plain text, so escape it before
        # wrapping it in <b> to keep the message valid HTML. The bell emoji
        # prefixes the title to flag it as a notification at a glance.
        title = html.quote(notification.title.upper())
        return f"<b>🔔 {title}</b>\n\n{notification.body}"

    def _build_reply_markup(self, notification: Notification) -> InlineKeyboardMarkup:
        # Deep-link the user to the relevant in-app page (root when path unset).
        url = self.web_config.build_url(notification.path or "/")
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Открыть приложение", url=url)]
            ]
        )

    async def send_notification(self, notification: Notification) -> None:
        user = await self.user_gateway.get_by_id(notification.user_id)
        if user is None or not user.settings.receive_telegram_notifications:
            raise UserNotReachable

        social_identity = await self.social_identity_gateway.get_by_provider(
            user_id=notification.user_id, provider=SocialProvider.TELEGRAM
        )
        # provider_user_id is the Bot API id, and it is optional — an identity
        # created from an `openid`-only token has no address to send to.
        if social_identity is None or social_identity.provider_user_id is None:
            raise UserNotReachable
        # End the read transaction before the Bot API call — sending touches no
        # DB, so holding the pooled connection across the network round-trip only
        # pins it needlessly under a mailing fan-out.
        await self.uow.rollback()
        try:
            await self.bot.send_message(
                chat_id=social_identity.provider_user_id,
                text=self._render_message_text(notification),
                parse_mode=ParseMode.HTML,
                reply_markup=self._build_reply_markup(notification),
            )
        except TelegramRetryAfter as e:
            raise NotificationRetryAfter(retry_after=e.retry_after) from e
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            raise UserNotReachable from e
        except TelegramUnauthorizedError as e:
            # Invalid bot token (e.g. the placeholder used when no real bot is
            # configured). This is a global misconfiguration, not a per-user
            # problem, so log it loudly. Treat as unreachable so the consumer
            # drops the message instead of redelivering it forever.
            # A concise one-liner, not a traceback: this fires on every
            # notification while the token is a placeholder, and the cause is
            # already chained onto the raised UserNotReachable.
            logger.error(  # noqa: TRY400
                "Telegram bot token is invalid or unauthorized — "
                "cannot deliver notifications via Telegram"
            )
            raise UserNotReachable from e
