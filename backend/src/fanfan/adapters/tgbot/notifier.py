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
from fanfan.application.ports.notifier import TelegramNotifierPort
from fanfan.core.exceptions.notifications import (
    NotificationChannelUnavailable,
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.config import WebConfig

logger = logging.getLogger(__name__)


class TelegramNotifier(TelegramNotifierPort):
    def __init__(
        self,
        bot: Bot,
        social_identity_gateway: SocialIdentityGateway,
        web_config: WebConfig,
    ) -> None:
        self.social_identity_gateway = social_identity_gateway
        self.bot = bot
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
        # Whether the user wants Telegram notifications is application policy,
        # checked by the SendNotification interactor before we get here; this
        # adapter only decides whether the user is physically reachable.
        social_identity = await self.social_identity_gateway.get_by_provider(
            user_id=notification.user_id, provider=SocialProvider.TELEGRAM
        )
        # provider_user_id is the Bot API id, and it is optional — an identity
        # created from an `openid`-only token has no address to send to.
        if social_identity is None or social_identity.provider_user_id is None:
            raise UserNotReachable
        try:
            await self.bot.send_message(
                chat_id=social_identity.provider_user_id,
                text=self._render_message_text(notification),
                parse_mode=ParseMode.HTML,
                reply_markup=self._build_reply_markup(notification),
            )
        except TelegramRetryAfter as e:
            raise NotificationRetryAfter(retry_after=e.retry_after) from e
        except TelegramForbiddenError as e:
            # The user blocked the bot or deleted their account — genuinely
            # unreachable, and nothing to log per delivery.
            raise UserNotReachable from e
        except TelegramBadRequest as e:
            # Telegram rejected the request itself — most likely the message HTML
            # failed to parse (a sanitizer/template regression), not a per-user
            # problem. Log the reason so the bug is diagnosable, then drop this
            # notification rather than redeliver a message that can never parse.
            logger.warning(
                "Telegram rejected notification as a bad request",
                extra={
                    "notification_id": str(notification.id),
                    "reason": e.message,
                },
            )
            raise UserNotReachable from e
        except TelegramUnauthorizedError as e:
            # Invalid bot token (e.g. the placeholder used when no real bot is
            # configured). This is a channel-wide misconfiguration, not a per-user
            # problem, so signal it as such: the consumer drops the message instead
            # of redelivering it forever (retrying can't fix a bad token). Logged
            # loudly as a concise one-liner, not a traceback — it fires on every
            # notification while the token is a placeholder, and the cause is
            # chained onto the raised exception.
            logger.error(  # noqa: TRY400
                "Telegram bot token is invalid or unauthorized — "
                "cannot deliver notifications via Telegram"
            )
            raise NotificationChannelUnavailable from e
