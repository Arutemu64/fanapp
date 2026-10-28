import html
import logging
from http import HTTPStatus
from typing import Any, override

from fanfan.adapters.rate_limiter import RateLimiter
from fanfan.adapters.tgbot.client import TelegramApiClient, TelegramApiError
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.notifier import TelegramNotifierPort
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    NotificationChannelUnavailable,
    NotificationRetryAfter,
    UserNotReachable,
    UserRevokedChannel,
)
from fanfan.core.models.notification import Notification
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.config import WebConfig

logger = logging.getLogger(__name__)

_MESSAGES_PER_SECOND = 25


class TelegramRateLimiter(RateLimiter):
    """The bot's send quota, shared by every concurrent send (APP scope).

    Its own type so the container can tell it from VK's limiter.
    """

    def __init__(self) -> None:
        super().__init__(per_second=_MESSAGES_PER_SECOND)


class TelegramNotifier(TelegramNotifierPort):
    def __init__(
        self,
        client: TelegramApiClient,
        social_identity_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        rate_limiter: TelegramRateLimiter,
        web_config: WebConfig,
    ) -> None:
        self.social_identity_gateway = social_identity_gateway
        self.client = client
        self.uow = uow
        self.rate_limiter = rate_limiter
        self.web_config = web_config

    @staticmethod
    def _render_message_text(notification: Notification) -> str:
        title = html.escape(notification.title.upper(), quote=False)
        return f"<b>🔔 {title}</b>\n\n{notification.body}"

    def _build_reply_markup(self, notification: Notification) -> dict[str, Any]:
        url = self.web_config.build_url(notification.path or "/")
        return {"inline_keyboard": [[{"text": "🌐 Открыть приложение", "url": url}]]}

    @override
    async def send_notification(self, notification: Notification) -> None:
        social_identity = await self.social_identity_gateway.get_by_provider(
            user_id=notification.user_id, provider=SocialProvider.TELEGRAM
        )
        if social_identity is None:
            raise UserNotReachable
        await self.uow.commit()
        await self.rate_limiter.wait()
        try:
            await self.client.send_message(
                chat_id=social_identity.provider_user_id,
                text=self._render_message_text(notification),
                reply_markup=self._build_reply_markup(notification),
            )
        except TelegramApiError as e:
            self._raise_for_error(notification, e)

    @staticmethod
    def _raise_for_error(notification: Notification, error: TelegramApiError) -> None:
        match error.status:
            case HTTPStatus.TOO_MANY_REQUESTS if error.retry_after is not None:
                raise NotificationRetryAfter(retry_after=error.retry_after) from error
            case HTTPStatus.FORBIDDEN:
                # The user blocked the bot or deleted their account.
                raise UserRevokedChannel from error
            case HTTPStatus.BAD_REQUEST:
                logger.warning(
                    "Telegram rejected notification as a bad request",
                    extra={
                        "notification_id": str(notification.id),
                        "reason": error.description,
                    },
                )
                raise UserNotReachable from error
            case HTTPStatus.UNAUTHORIZED:
                logger.error(
                    "Telegram bot token is invalid or unauthorized — "
                    "cannot deliver notifications via Telegram"
                )
                raise NotificationChannelUnavailable from error
            case _:
                raise error
