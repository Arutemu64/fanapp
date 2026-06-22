import logging

import aiohttp
import nh3
from webpush import WebPush, WebPushSubscription
from webpush.vapid import VAPIDException

from fanfan.adapters.push.config import PushConfig
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.notifier import Notifier
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import NotificationChannelUnavailable
from fanfan.core.models.notification import Notification, NotificationRevocation
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)


class PushNotifier(Notifier):
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        uow: UnitOfWork,
        push_config: PushConfig,
    ) -> None:
        self.push_sub_gateway = push_sub_gateway
        self.uow = uow
        self.push_config = push_config
        self._wp: WebPush | None = None

    def _get_web_push(self) -> WebPush:
        # Build WebPush lazily (and cache it) so missing or invalid VAPID keys
        # surface here, at send time inside the consumer's try/except, rather
        # than at DI-resolution time where the error can't be caught and the
        # NATS message would be redelivered forever.
        if self._wp is None:
            try:
                self._wp = WebPush(
                    private_key=self.push_config.private_key_path,
                    public_key=self.push_config.public_key_path,
                    subscriber=self.push_config.subscriber,
                )
            except (VAPIDException, ValueError) as e:
                logger.error(  # noqa: TRY400
                    "VAPID keys are missing or invalid — cannot send push notifications"
                )
                raise NotificationChannelUnavailable from e
        return self._wp

    @staticmethod
    def _sanitize_text(text: str) -> str:
        # Replace HTML line breaks with \n
        text = text.replace("<br>", "\n")
        # Remove rest HTML tags
        return nh3.clean(text, tags=set())

    async def _deliver_to_user(self, user_id: UserId, data: dict) -> None:
        # Resolve WebPush up front so a misconfigured channel fails fast (and is
        # caught by the consumer) before we open a session or hit the gateway.
        self._get_web_push()
        push_subs = await self.push_sub_gateway.list_by_user(user_id)
        async with aiohttp.ClientSession() as session:
            for sub in push_subs:
                subscription = WebPushSubscription.model_validate(
                    {
                        "endpoint": sub.endpoint,
                        "keys": {"auth": sub.auth, "p256dh": sub.p256dh},
                    }
                )
                message = self._get_web_push().get(
                    message=data, subscription=subscription, ttl=3600
                )
                async with session.post(
                    url=str(subscription.endpoint),
                    data=message.encrypted,
                    # WebPushHeaders is an all-str TypedDict; the checker won't
                    # narrow its values to str, so it rejects the Mapping type.
                    headers=message.headers,  # type: ignore  # noqa: PGH003
                ) as response:
                    if response.status in [404, 410]:
                        await self.push_sub_gateway.delete(sub)
                        await self.uow.commit()

    async def send_notification(self, notification: Notification) -> None:
        data = {
            "tag": str(notification.id),
            "title": self._sanitize_text(notification.title),
            "body": self._sanitize_text(notification.body),
            # Deep-link the service worker navigates to on click; root when unset.
            "url": notification.path or "/",
            # Test pushes must always render the OS notification, even when the
            # app is in the foreground (the service worker otherwise suppresses
            # it to avoid duplicating the in-app toast).
            "test": notification.type == NotificationType.TEST,
        }
        await self._deliver_to_user(notification.user_id, data)

    async def revoke_notification(self, revocation: NotificationRevocation) -> None:
        # Silent revoke: the service worker closes the OS notification carrying
        # this tag without rendering anything new. Best-effort — only reaches
        # devices that are online to receive the push.
        data = {"tag": str(revocation.notification_id), "revoke": True}
        await self._deliver_to_user(revocation.user_id, data)
