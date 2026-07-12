import logging

import httpx2
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
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationType

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
        # Push uses plain text; convert <br> to newlines then strip all HTML.
        text = text.replace("<br>", "\n")
        return nh3.clean(text, tags=set())

    def _build_message(self, subscription_info: dict, notification: Notification):
        subscription_info = {
            "endpoint": subscription_info["endpoint"],
            "keys": {
                "auth": subscription_info["auth"],
                "p256dh": subscription_info["p256dh"],
            },
        }
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
        push_subscription = WebPushSubscription.model_validate(subscription_info)
        message = self._get_web_push().get(
            message=data, subscription=push_subscription, ttl=3600
        )
        return push_subscription, message

    async def send_notification(self, notification: Notification) -> None:
        # Resolve WebPush up front so a misconfigured channel fails fast (and is
        # caught by the consumer) before we open a session or hit the gateway.
        self._get_web_push()
        push_subs = await self.push_sub_gateway.list_by_user(notification.user_id)
        async with httpx2.AsyncClient() as client:
            for sub in push_subs:
                subscription, message = self._build_message(
                    {
                        "endpoint": sub.endpoint,
                        "auth": sub.auth,
                        "p256dh": sub.p256dh,
                    },
                    notification,
                )
                response = await client.post(
                    url=str(subscription.endpoint),
                    content=message.encrypted,
                    headers=message.headers,
                )
                if response.status_code in [404, 410]:
                    await self.push_sub_gateway.delete(sub)
                    await self.uow.commit()
