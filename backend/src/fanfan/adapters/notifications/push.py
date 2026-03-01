from pathlib import Path

import aiohttp
import nh3
from webpush import WebPush, WebPushSubscription

from fanfan.adapters.db.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.notifier import Notifier
from fanfan.core.models.notification import Notification


class PushNotifier(Notifier):
    def __init__(
        self, push_sub_gateway: PushSubscriptionGateway, uow: UnitOfWork
    ) -> None:
        self.push_sub_gateway = push_sub_gateway
        self.uow = uow
        # TODO Move these to config
        self.wp = WebPush(
            private_key=Path("./private_key.pem"),
            public_key=Path("./public_key.pem"),
            subscriber="arutemu64@outlook.com",
        )

    @staticmethod
    def _sanitize_text(text: str) -> str:
        # Replace HTML line breaks with \n
        text = text.replace("<br>", "\n")
        # Remove rest HTML tags
        return nh3.clean(text, tags=set())

    async def send_notification(self, notification: Notification) -> None:
        push_subs = await self.push_sub_gateway.list_user_push_subs(
            notification.user_id
        )
        async with aiohttp.ClientSession() as session:
            for sub in push_subs:
                subscription_info = {
                    "endpoint": sub.endpoint,
                    "keys": {"auth": sub.auth, "p256dh": sub.p256dh},
                }
                data = {
                    "tag": str(notification.id),
                    "title": self._sanitize_text(notification.title),
                    "body": self._sanitize_text(notification.body),
                    "url": "/",
                }
                subscription = WebPushSubscription.model_validate(subscription_info)
                message = self.wp.get(message=data, subscription=subscription, ttl=3600)
                async with session.post(
                    url=str(subscription.endpoint),
                    data=message.encrypted,
                    headers=message.headers,
                ) as response:
                    if response.status in [404, 410]:
                        async with self.uow:
                            await self.push_sub_gateway.delete_push_subscription(sub)
                            await self.uow.commit()
