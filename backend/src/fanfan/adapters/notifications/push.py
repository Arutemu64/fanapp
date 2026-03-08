import aiohttp
import nh3
from webpush import WebPush, WebPushSubscription

from fanfan.adapters.db.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.notifications.config import PushConfig
from fanfan.application.common.notifier import Notifier
from fanfan.core.models.notification import Notification


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
        }
        push_subscription = WebPushSubscription.model_validate(subscription_info)
        message = self.wp.get(message=data, subscription=push_subscription, ttl=3600)
        return push_subscription, message

    async def send_notification(self, notification: Notification) -> None:
        push_subs = await self.push_sub_gateway.list_user_push_subs(
            notification.user_id
        )
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
                        async with self.uow:
                            await self.push_sub_gateway.delete_push_subscription(sub)
                            await self.uow.commit()
