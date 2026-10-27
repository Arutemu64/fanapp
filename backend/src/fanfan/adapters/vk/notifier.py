import html
import logging

import nh3

from fanfan.adapters.vk.client import VkApiClient, VkApiError
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.notifier import VkNotifierPort
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    NotificationChannelUnavailable,
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.config import WebConfig

logger = logging.getLogger(__name__)

_USER_UNREACHABLE_CODES = frozenset({7, 15, 901, 902})
_FLOOD_CODES = frozenset({6, 9})
_AUTH_CODES = frozenset({5, 27, 28})

_FLOOD_RETRY_AFTER_SECONDS = 1


class VkNotifier(VkNotifierPort):
    def __init__(
        self,
        client: VkApiClient,
        social_identity_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        web_config: WebConfig,
    ) -> None:
        self.client = client
        self.social_identity_gateway = social_identity_gateway
        self.uow = uow
        self.web_config = web_config

    def _render_message_text(self, notification: Notification) -> str:
        body = html.unescape(
            nh3.clean(notification.body.replace("<br>", "\n"), tags=set())
        )
        url = self.web_config.build_url(notification.path or "/")
        return (
            f"🔔 {notification.title.upper()}\n\n{body}\n\n🌐 Открыть приложение: {url}"
        )

    async def send_notification(self, notification: Notification) -> None:
        social_identity = await self.social_identity_gateway.get_by_provider(
            user_id=notification.user_id, provider=SocialProvider.VK
        )
        if social_identity is None:
            raise UserNotReachable
        await self.uow.commit()

        message_id: int
        try:
            message_id = await self.client.send_message(
                peer_id=social_identity.provider_user_id,
                message=self._render_message_text(notification),
            )
        except VkApiError as e:
            self._handle_api_error(e, notification)
            raise

        await self._delete_group_copy(message_id=message_id, notification=notification)

    async def _delete_group_copy(
        self, *, message_id: int, notification: Notification
    ) -> None:
        try:
            await self.client.delete_message(message_id=message_id)
        except Exception:
            logger.warning(
                "Failed to delete VK group copy of notification %s",
                notification.id,
                exc_info=True,
            )

    @staticmethod
    def _handle_api_error(error: VkApiError, notification: Notification) -> None:
        if error.code in _FLOOD_CODES:
            raise NotificationRetryAfter(
                retry_after=_FLOOD_RETRY_AFTER_SECONDS
            ) from error
        if error.code in _USER_UNREACHABLE_CODES:
            raise UserNotReachable from error
        if error.code in _AUTH_CODES:
            logger.error(
                "VK group token is invalid or unauthorized — "
                "cannot deliver notifications via VK",
                extra={"error_code": error.code},
            )
            raise NotificationChannelUnavailable from error
        logger.warning(
            "Unhandled VK API error sending notification",
            extra={
                "error_code": error.code,
                "notification_id": str(notification.id),
            },
        )
        raise error
