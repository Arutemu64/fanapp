import logging

import nh3

from fanfan.adapters.push.client import MessageData, WebPushClient
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.notifier import Notifier
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationType

logger = logging.getLogger(__name__)

# Push services return these when a subscription is gone (unsubscribed or
# expired); we prune it so we stop trying to reach a dead endpoint.
_GONE_STATUS_CODES = frozenset({404, 410})


class PushNotifier(Notifier):
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        uow: UnitOfWork,
        client: WebPushClient,
    ) -> None:
        self.push_sub_gateway = push_sub_gateway
        self.uow = uow
        self.client = client

    @staticmethod
    def _sanitize_text(text: str) -> str:
        # Push uses plain text; convert <br> to newlines then strip all HTML.
        text = text.replace("<br>", "\n")
        return nh3.clean(text, tags=set())

    def _build_message_data(self, notification: Notification) -> MessageData:
        # Identical for every subscription of this user, so build it once; only
        # the per-subscription encryption downstream varies.
        return {
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

    async def send_notification(self, notification: Notification) -> None:
        # Resolve WebPush up front so a misconfigured channel fails fast (and is
        # caught by the consumer) before we hit the gateway.
        self.client.ensure_available()
        push_subs = await self.push_sub_gateway.list_by_user(notification.user_id)
        # End the read transaction before the network sends below. Sending is
        # read-only towards the DB (only pruning a dead endpoint writes), yet a
        # webpush round-trip is slow and we loop it per subscription — holding
        # the pooled connection across it would, under a mailing fan-out, pin one
        # connection per in-flight notification and exhaust the pool. Releasing
        # here returns it for the duration of the sends; a prune re-opens a short
        # transaction of its own.
        await self.uow.rollback()
        message_data = self._build_message_data(notification)
        for sub in push_subs:
            status_code = await self.client.send(
                subscription=sub,
                message_data=message_data,
            )
            if status_code in _GONE_STATUS_CODES:
                await self.push_sub_gateway.delete(sub)
                await self.uow.commit()
