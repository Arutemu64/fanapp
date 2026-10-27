import logging
from typing import Any, Literal, TypedDict, cast

import httpx2
from pydantic import AnyHttpUrl
from webpush import WebPush, WebPushSubscription
from webpush.types import WebPushKeys
from webpush.vapid import VAPIDException

from fanfan.adapters.push.config import PushConfig
from fanfan.core.exceptions.notifications import NotificationChannelUnavailable
from fanfan.core.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)

PushUrgency = Literal["very-low", "low", "normal", "high"]


class NotificationData(TypedDict):
    test: bool


class DeclarativeNotification(TypedDict):
    title: str
    body: str
    navigate: str
    tag: str
    renotify: bool
    data: NotificationData


class MessageData(TypedDict):
    """A Declarative Web Push message (W3C Push API draft).

    Safari 18.4+ Home Screen apps show it without running the service worker's
    `push` handler; other browsers hand the same JSON to that handler. WebKit
    revokes the subscription of an imperative handler that skips a notification,
    which ours does while the app is visible, and the declarative path carries
    no such penalty: https://webkit.org/blog/16535/meet-declarative-web-push/
    Serialized to JSON by the library, so every value must be JSON-native.
    """

    web_push: Literal[8030]
    notification: DeclarativeNotification
    mutable: bool


class WebPushClient:
    def __init__(self, client: httpx2.AsyncClient, config: PushConfig) -> None:
        self._client = client
        self._config = config
        self._wp: WebPush | None = None

    def _get_web_push(self) -> WebPush:
        if self._wp is None:
            try:
                self._wp = WebPush(
                    private_key=self._config.private_key_path,
                    public_key=self._config.public_key_path,
                    subscriber=self._config.subscriber,
                )
            except (VAPIDException, ValueError) as e:
                logger.error(  # noqa: TRY400
                    "VAPID keys are missing or invalid — cannot send push notifications"
                )
                raise NotificationChannelUnavailable from e
        return self._wp

    def ensure_available(self) -> None:
        self._get_web_push()

    async def send(
        self,
        *,
        subscription: PushSubscription,
        message_data: MessageData,
        ttl_seconds: int,
        urgency: PushUrgency,
        topic: str | None,
    ) -> httpx2.Response:
        push_subscription = WebPushSubscription(
            endpoint=cast("AnyHttpUrl", subscription.endpoint),
            keys=WebPushKeys(auth=subscription.auth, p256dh=subscription.p256dh),
        )
        message = self._get_web_push().get(
            message=cast("dict[Any, Any]", message_data),
            subscription=push_subscription,
            ttl=ttl_seconds,
        )
        headers = {**cast("dict[str, str]", message.headers), "urgency": urgency}
        if topic is not None:
            headers["topic"] = topic
        return await self._client.post(
            url=str(push_subscription.endpoint),
            content=message.encrypted,
            headers=headers,
        )
