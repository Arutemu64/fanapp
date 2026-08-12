import logging
from typing import cast

import httpx2
from webpush import WebPush, WebPushSubscription
from webpush.vapid import VAPIDException

from fanfan.adapters.push.config import PushConfig
from fanfan.core.exceptions.notifications import NotificationChannelUnavailable

logger = logging.getLogger(__name__)


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

    async def send(self, *, subscription_info: dict, message_data: dict) -> int:
        # Encrypt per subscription (each has its own keys) and POST to that
        # endpoint. Returns the HTTP status so the notifier can prune a
        # subscription the push service has retired (404/410).
        push_subscription = WebPushSubscription.model_validate(subscription_info)
        message = self._get_web_push().get(
            message=message_data, subscription=push_subscription, ttl=3600
        )
        response = await self._client.post(
            url=str(push_subscription.endpoint),
            content=message.encrypted,
            # message.headers is a TypedDict (all-str values); httpx wants a plain
            # Mapping[str, str], which a TypedDict is not assignable to.
            headers=cast("dict[str, str]", message.headers),
        )
        return response.status_code
