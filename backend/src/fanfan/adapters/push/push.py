import aiohttp
import nh3
from webpush import WebPush, WebPushSubscription

from fanfan.adapters.push.config import PushConfig
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.notifier import Notifier
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationType


class PushNotifier(Notifier):
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        uow: UnitOfWork,
        push_config: PushConfig,
    ) -> None:
        self.push_sub_gateway = push_sub_gateway
        self.uow = uow
        self.wp = WebPush(
            private_key=push_config.private_key_path,
            public_key=push_config.public_key_path,
            subscriber=push_config.subscriber,
        )

    @staticmethod
    def _sanitize_text(text: str) -> str:
        # Replace HTML line breaks with \n
        text = text.replace("<br>", "\n")
        # Remove rest HTML tags
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
            "url": "/",
            # Test pushes must always render the OS notification, even when the
            # app is in the foreground (the service worker otherwise suppresses
            # it to avoid duplicating the in-app toast).
            "test": notification.type == NotificationType.TEST,
        }
        push_subscription = WebPushSubscription.model_validate(subscription_info)
        message = self.wp.get(message=data, subscription=push_subscription, ttl=3600)
        return push_subscription, message

    async def send_notification(self, notification: Notification) -> None:
        push_subs = await self.push_sub_gateway.list_by_user(notification.user_id)
        async with aiohttp.ClientSession() as session:
            for sub in push_subs:
                subscription, message = self._build_message(
                    {
                        "endpoint": sub.endpoint,
                        "auth": sub.auth,
                        "p256dh": sub.p256dh,
                    },
                    notification,
                )
                async with session.post(
                    url=str(subscription.endpoint),
                    data=message.encrypted,
                    headers=message.headers,
                ) as response:
                    if response.status in [404, 410]:
                        await self.push_sub_gateway.delete(sub)
                        await self.uow.commit()
