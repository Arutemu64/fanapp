import html
import logging
import re
from typing import Any, override

import nh3

from fanfan.adapters.notification_button import button_label_for
from fanfan.adapters.vk.client import VkApiClient, VkApiError
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.notifier import VkNotifierPort
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    NotificationChannelUnavailable,
    NotificationRetryAfter,
    UserNotReachable,
    UserRevokedChannel,
)
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.config import WebConfig

logger = logging.getLogger(__name__)

# messages.send error codes: https://dev.vk.com/ru/method/messages.send
# Blacklisted the community, withdrew consent, privacy settings forbid it.
_USER_REVOKED_CODES = frozenset({900, 901, 902})
_USER_UNREACHABLE_CODES = frozenset({7, 15, 987, 988, 1021})
_FLOOD_CODES = frozenset({6, 9})
_AUTH_CODES = frozenset({5, 27, 28})
# The keyboard is malformed, or the community has bot features switched off.
_KEYBOARD_CODES = frozenset({911, 912})

_FLOOD_RETRY_AFTER_SECONDS = 1

# VK drops a repeated non-zero int32 random_id in the same dialog for an hour.
_INT32_MAX = 2**31 - 1


# The sanitizer emits exactly this shape: ``href`` is the only attribute it keeps.
_LINK = re.compile(r'<a href="([^"]*)">(.*?)</a>', re.DOTALL)


def _link_as_text(match: re.Match[str]) -> str:
    href = str(match.group(1))
    text = str(match.group(2))
    if text == href:
        return href
    return f"{text} ({href})"


def _random_id_for(notification_id: NotificationId) -> int:
    """A stable, non-zero int32, so a JetStream redelivery cannot send twice."""
    return notification_id.int % _INT32_MAX + 1


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

    @staticmethod
    def _render_message_text(notification: Notification) -> str:
        # VK shows no markup, so a link keeps its target as visible text.
        body = _LINK.sub(_link_as_text, notification.body)
        body = html.unescape(nh3.clean(body, tags=set()))
        return f"🔔 {notification.title.upper()}\n\n{body}"

    def _build_keyboard(self, notification: Notification) -> dict[str, Any]:
        button = {
            "action": {
                "type": "open_link",
                "link": self.web_config.build_url(notification.path or "/"),
                "label": button_label_for(notification.path),
            }
        }
        return {"inline": True, "buttons": [[button]]}

    @override
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
                random_id=_random_id_for(notification.id),
                keyboard=self._build_keyboard(notification),
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
        if error.code in _USER_REVOKED_CODES:
            raise UserRevokedChannel from error
        if error.code in _USER_UNREACHABLE_CODES:
            raise UserNotReachable from error
        if error.code in _AUTH_CODES:
            logger.error(
                "VK group token is invalid or unauthorized — "
                "cannot deliver notifications via VK",
                extra={"error_code": error.code},
            )
            raise NotificationChannelUnavailable from error
        if error.code in _KEYBOARD_CODES:
            logger.error(
                "VK refused the notification keyboard — enable bot features "
                "in the community settings",
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
