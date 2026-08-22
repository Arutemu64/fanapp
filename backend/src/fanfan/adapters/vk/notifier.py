import logging

import nh3

from fanfan.adapters.vk.client import VkApiClient, VkApiError
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

# VK error codes we translate. 901/902 mean the group may not message this
# user (they never allowed messages, or their privacy settings forbid it); 7/15
# are the generic permission/access-denied variants of the same. 6/9 are flood
# control. 5/27/28 are token/authorization failures — a channel-wide
# misconfiguration, not a per-user problem.
# https://dev.vk.ru/en/reference/errors
_USER_UNREACHABLE_CODES = frozenset({7, 15, 901, 902})
_FLOOD_CODES = frozenset({6, 9})
_AUTH_CODES = frozenset({5, 27, 28})

# VK gives no retry hint on flood control, so back off a fixed short interval
# before the consumer redelivers.
_FLOOD_RETRY_AFTER_SECONDS = 1


class VkNotifier(Notifier):
    def __init__(
        self,
        client: VkApiClient,
        user_gateway: UserGateway,
        social_identity_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        web_config: WebConfig,
    ) -> None:
        self.client = client
        self.user_gateway = user_gateway
        self.social_identity_gateway = social_identity_gateway
        self.uow = uow
        self.web_config = web_config

    def _render_message_text(self, notification: Notification) -> str:
        # VK group messages are plain text (no HTML). The stored body is a
        # safe HTML subset, so strip every tag the same way the push adapter
        # does, turning <br> into newlines first. VK auto-links the bare URL, so
        # a trailing "open the app" line replaces Telegram's inline button.
        body = nh3.clean(notification.body.replace("<br>", "\n"), tags=set())
        url = self.web_config.build_url(notification.path or "/")
        return (
            f"🔔 {notification.title.upper()}\n\n{body}\n\n🌐 Открыть приложение: {url}"
        )

    async def send_notification(self, notification: Notification) -> None:
        user = await self.user_gateway.get_by_id(notification.user_id)
        if user is None or not user.settings.receive_vk_notifications:
            raise UserNotReachable

        social_identity = await self.social_identity_gateway.get_by_provider(
            user_id=notification.user_id, provider=SocialProvider.VK
        )
        # provider_user_id is the VK numeric user id we message. Guarded the same
        # way the Telegram notifier guards its address: an unlinked user has no
        # identity at all, which is the real unreachable case here.
        if social_identity is None:
            raise UserNotReachable

        # End the read transaction before the VK API calls — sending (and the
        # best-effort group-copy delete) touches no DB, so holding the pooled
        # connection across the network round-trip only pins it needlessly under
        # a mailing fan-out.
        await self.uow.rollback()

        message_id: int
        try:
            message_id = await self.client.send_message(
                peer_id=social_identity.provider_user_id,
                message=self._render_message_text(notification),
            )
        except VkApiError as e:
            self._handle_api_error(e, notification)
            raise  # _handle_api_error always raises; this keeps message_id bound

        await self._delete_group_copy(message_id=message_id, notification=notification)

    async def _delete_group_copy(
        self, *, message_id: int, notification: Notification
    ) -> None:
        # The message is already delivered; this only tidies the group's own copy
        # out of the community inbox organizers see. Best-effort on purpose: a
        # failed cleanup must not fail the notification, or the consumer would
        # redeliver and re-send a duplicate to the user. Swallow everything —
        # a VK error, a network blip — so delivery stands regardless.
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
            # The group token is invalid or lacks the messages scope. This is
            # a global misconfiguration, not a per-user problem, so log it loudly.
            # A concise one-liner, not a traceback: it fires on every VK
            # notification while the token is broken, and the cause is chained
            # onto the raised UserNotReachable. Treated as unreachable so the
            # consumer drops the message instead of redelivering it forever.
            logger.error(
                "VK group token is invalid or unauthorized (code %s) — "
                "cannot deliver notifications via VK",
                error.code,
            )
            raise UserNotReachable from error
        # An unfamiliar VK error — let it propagate so the consumer nacks and the
        # failure surfaces, rather than silently swallowing an unknown condition.
        logger.warning(
            "Unhandled VK API error %s sending notification %s",
            error.code,
            notification.id,
        )
        raise error
