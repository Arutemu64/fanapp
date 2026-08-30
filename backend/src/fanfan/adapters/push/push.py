import html
import logging

import httpx2
import nh3

from fanfan.adapters.push.client import MessageData, WebPushClient
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.notifier import PushNotifierPort
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    NotificationChannelUnavailable,
    NotificationRetryAfter,
)
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationType

logger = logging.getLogger(__name__)

# Push service status codes we act on, per RFC 8030 §8.4 and the WebPush error
# conventions (https://www.rfc-editor.org/rfc/rfc8030). 404/410 mean the
# subscription is gone (unsubscribed or expired) — prune it so we stop trying a
# dead endpoint. 400/401/403 are VAPID/auth failures — a channel-wide
# misconfiguration no retry can fix. 429 and 5xx are transient — retry later.
_GONE_STATUS_CODES = frozenset({404, 410})
_CHANNEL_UNAVAILABLE_STATUS_CODES = frozenset({400, 401, 403})
_TOO_MANY_REQUESTS = 429
_CLIENT_ERROR_STATUS = 400
_SERVER_ERROR_STATUS = 500

# When a 429 carries no usable Retry-After hint, back off a fixed short interval
# before the consumer redelivers.
_RETRY_AFTER_DEFAULT_SECONDS = 5


class PushNotifier(PushNotifierPort):
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
        # Push shows plain text: turn <br> into newlines, strip every tag, then
        # decode HTML entities. nh3 leaves entities encoded (&amp;, &lt;), so
        # without the final unescape a body like "5 < 10 & up" would surface in
        # the OS notification as "5 &lt; 10 &amp; up". Strip before unescaping so
        # decoded text is never re-interpreted as markup.
        text = text.replace("<br>", "\n")
        return html.unescape(nh3.clean(text, tags=set()))

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
        message_data = self._build_message_data(notification)
        # A user may have several subscriptions (one per device/browser). Deliver
        # to every reachable one this pass, then retry the whole notification only
        # if some endpoint was transiently unavailable — the shared `tag` lets the
        # OS collapse the redelivered copy on endpoints that already succeeded.
        retry_after: int | None = None
        for sub in push_subs:
            response = await self.client.send(
                subscription=sub,
                message_data=message_data,
            )
            status_code = response.status_code
            if status_code in _GONE_STATUS_CODES:
                await self.push_sub_gateway.delete(sub)
                await self.uow.commit()
            elif status_code in _CHANNEL_UNAVAILABLE_STATUS_CODES:
                # A VAPID/auth failure rejects every subscription equally, so stop
                # and let the consumer drop the message — retrying can't fix a
                # channel-wide config error.
                logger.error(
                    "Push service rejected notification — VAPID keys or "
                    "authorization are misconfigured",
                    extra={
                        "notification_id": str(notification.id),
                        "status_code": status_code,
                    },
                )
                raise NotificationChannelUnavailable
            elif (
                status_code == _TOO_MANY_REQUESTS or status_code >= _SERVER_ERROR_STATUS
            ):
                # Throttled or a push-service outage — transient, so ask the
                # consumer to redeliver later instead of dropping the message.
                retry_after = self._retry_after_seconds(response)
                logger.warning(
                    "Push service throttled or failed; will retry",
                    extra={
                        "notification_id": str(notification.id),
                        "status_code": status_code,
                        "retry_after": retry_after,
                    },
                )
            elif status_code >= _CLIENT_ERROR_STATUS:
                # An unexpected failure we don't specifically translate (e.g. 413
                # payload too large). Log it so it's diagnosable; skip this
                # endpoint without pruning, since the cause may be per-message.
                logger.warning(
                    "Unexpected push service status",
                    extra={
                        "notification_id": str(notification.id),
                        "status_code": status_code,
                    },
                )
        if retry_after is not None:
            raise NotificationRetryAfter(retry_after=retry_after)

    @staticmethod
    def _retry_after_seconds(response: httpx2.Response) -> int:
        # Honor the push service's Retry-After when it gives a delta-seconds hint;
        # fall back to a fixed short interval otherwise (the HTTP-date form is rare
        # from push services and not worth parsing here).
        raw = response.headers.get("Retry-After")
        if raw is not None:
            try:
                parsed = int(raw)
            except ValueError:
                parsed = 0
            if parsed > 0:
                return parsed
        return _RETRY_AFTER_DEFAULT_SECONDS
