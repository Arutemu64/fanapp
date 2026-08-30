import logging
from typing import Any, TypedDict, cast

import httpx2
from pydantic import AnyHttpUrl
from webpush import WebPush, WebPushSubscription
from webpush.types import WebPushKeys
from webpush.vapid import VAPIDException

from fanfan.adapters.push.config import PushConfig
from fanfan.core.exceptions.notifications import NotificationChannelUnavailable
from fanfan.core.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)

# How long a push service holds an undelivered message before discarding it. One
# hour: a convention notification is stale well before then, and the service
# worker collapses a late duplicate by its `tag` anyway.
_PUSH_TTL_SECONDS = 3600


class MessageData(TypedDict):
    # The payload the service worker unpacks in its `push` handler. Serialized to
    # JSON by the library, so every value must be JSON-native.
    tag: str
    title: str
    body: str
    url: str
    test: bool


class WebPushClient:
    # Owns the VAPID signer and a shared httpx2.AsyncClient. The client (with its
    # timeout) is configured once in the DI provider and reused across every push,
    # so bursts to the same push service reuse the connection pool instead of
    # re-handshaking per message (https://www.python-httpx.org/advanced/clients/).
    # Provided at APP scope so both the pool and the VAPID signer outlive the
    # per-message request scope; the WebPush signer is now built once for the
    # process rather than once per notification.
    def __init__(self, client: httpx2.AsyncClient, config: PushConfig) -> None:
        self._client = client
        self._config = config
        self._wp: WebPush | None = None

    def _get_web_push(self) -> WebPush:
        # Build WebPush lazily (and cache it) so missing or invalid VAPID keys
        # surface here, at send time inside the consumer's try/except, rather
        # than at DI-resolution time where the error can't be caught and the
        # NATS message would be redelivered forever.
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
        # Let the notifier resolve WebPush up front so a misconfigured channel
        # fails fast (and is caught by the consumer) before it hits the gateway.
        self._get_web_push()

    async def send(
        self, *, subscription: PushSubscription, message_data: MessageData
    ) -> httpx2.Response:
        # Encrypt per subscription (each has its own keys) and POST to that
        # endpoint. Returns the raw response so the notifier can act on the push
        # service's status: prune a retired subscription (404/410), honor a 429's
        # Retry-After, or flag a channel-wide auth failure (400/401/403).
        # The library's WebPushSubscription nests the keys under `keys`; our
        # domain model keeps them flat, so map explicitly here rather than
        # feeding it a dict of the wrong shape.
        push_subscription = WebPushSubscription(
            endpoint=cast("AnyHttpUrl", subscription.endpoint),
            keys=WebPushKeys(auth=subscription.auth, p256dh=subscription.p256dh),
        )
        message = self._get_web_push().get(
            # get() types `message` as dict[Any, Any]; a TypedDict is not
            # assignable to an invariant dict, so cast. get() only reads it
            # (json.dumps), never mutating, so the cast is sound.
            message=cast("dict[Any, Any]", message_data),
            subscription=push_subscription,
            ttl=_PUSH_TTL_SECONDS,
        )
        return await self._client.post(
            url=str(push_subscription.endpoint),
            content=message.encrypted,
            # message.headers is a TypedDict (all-str values); httpx wants a plain
            # Mapping[str, str], which a TypedDict is not assignable to.
            headers=cast("dict[str, str]", message.headers),
        )
