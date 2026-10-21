import asyncio
import html
import logging
from datetime import timedelta
from http import HTTPStatus

import httpx2
import nh3

from fanfan.adapters.push.client import MessageData, PushUrgency, WebPushClient
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
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.notification import (
    SCHEDULE_NOTIFICATION_LIFETIME,
    NotificationType,
)
from fanfan.presentation.web.config import WebConfig

logger = logging.getLogger(__name__)

# Push service status codes we act on, per RFC 8030 §8.4 and the WebPush error
# conventions (https://www.rfc-editor.org/rfc/rfc8030). 404/410 mean the
# subscription is gone (unsubscribed or expired) — prune it so we stop trying a
# dead endpoint. 400/401/403 are VAPID/auth failures — a channel-wide
# misconfiguration no retry can fix. 429 and 5xx are transient — retry later.
_GONE_STATUS_CODES = frozenset({404, 410})
_CHANNEL_UNAVAILABLE_STATUS_CODES = frozenset({400, 401, 403})

# When a 429 carries no usable Retry-After hint, back off a fixed short interval
# before the consumer redelivers.
_RETRY_AFTER_DEFAULT_SECONDS = 5

# How long a push service holds an undelivered message before discarding it
# (RFC 8030 §5.2). One hour for most: a convention notification is stale well
# before then, and the service worker collapses a late duplicate by its `tag`
# anyway. A schedule notification expires with its text.
_DEFAULT_TTL = timedelta(hours=1)

# Notification types that share a device-level topic, so a burst collapses to the
# latest instead of stacking: on the OS shade through the `tag`, and at the push
# service through the Topic header (RFC 8030 §5.4), which replaces a message still
# waiting for an offline device, so it wakes up to the current state only.
# Schedule updates flip rapidly during a live event (the reader only cares about
# the current state); organizer broadcasts share one "broadcast" lane. A type
# absent here keeps a unique tag (its notification id) and sends no Topic, so
# distinct notifications never replace one another. Topic values must stay
# within 32 base64url characters.
_TOPIC_TAGS: dict[NotificationType, str] = {
    NotificationType.SCHEDULE_CHANGE: "schedule",
    NotificationType.SCHEDULE_SUBSCRIPTION: "schedule",
    NotificationType.BROADCAST: "broadcast",
}


class PushNotifier(PushNotifierPort):
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        uow: UnitOfWork,
        client: WebPushClient,
        web_config: WebConfig,
    ) -> None:
        self.push_sub_gateway = push_sub_gateway
        self.uow = uow
        self.client = client
        self.web_config = web_config

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
        topic = _TOPIC_TAGS.get(notification.type)
        return {
            "web_push": 8030,
            "mutable": True,
            "notification": {
                "title": self._sanitize_text(notification.title),
                "body": self._sanitize_text(notification.body),
                # Deep link opened on click; the app root when unset.
                "navigate": self.web_config.build_url(notification.path or "/"),
                # A topic tag groups the notification with its lane so a new one
                # replaces the displayed one; renotify keeps that replacement
                # alerting. Falls back to the notification id, which still
                # collapses re-pushes of the same notification across a user's
                # devices without grouping.
                "tag": topic or str(notification.id),
                "renotify": topic is not None,
                "data": {"test": notification.type == NotificationType.TEST},
            },
        }

    async def _send_to_devices(
        self, notification: Notification, push_subs: list[PushSubscription]
    ) -> list[httpx2.Response | BaseException]:
        message_data = self._build_message_data(notification)
        topic = _TOPIC_TAGS.get(notification.type)
        ttl = _DEFAULT_TTL
        urgency: PushUrgency = "normal"
        if notification.type.is_schedule:
            ttl = SCHEDULE_NOTIFICATION_LIFETIME
            urgency = "high"
        # Every device's outcome is acted on (prune, retry) even when one send
        # failed outright, so failures come back as results, not raised.
        return await asyncio.gather(
            *(
                self.client.send(
                    subscription=sub,
                    message_data=message_data,
                    ttl_seconds=int(ttl.total_seconds()),
                    urgency=urgency,
                    topic=topic,
                )
                for sub in push_subs
            ),
            return_exceptions=True,
        )

    async def send_notification(self, notification: Notification) -> None:
        # Resolve WebPush up front so a misconfigured channel fails fast (and is
        # caught by the consumer) before we hit the gateway.
        self.client.ensure_available()
        push_subs = await self.push_sub_gateway.list_by_user(notification.user_id)
        # End the read before the sends, so the pooled connection is not held
        # while the push services answer.
        await self.uow.commit()
        # A user may have several subscriptions (one per device/browser), sent to
        # at once. Deliver to every reachable one this pass, then retry the whole
        # notification only if some endpoint was transiently unavailable — the
        # shared `tag` lets the OS collapse the redelivered copy on endpoints that
        # already succeeded.
        responses = await self._send_to_devices(notification, push_subs)
        retry_after: int | None = None
        send_error: BaseException | None = None
        for sub, response in zip(push_subs, responses, strict=True):
            if isinstance(response, BaseException):
                send_error = send_error or response
                continue
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
                status_code == HTTPStatus.TOO_MANY_REQUESTS
                or status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
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
            elif status_code >= HTTPStatus.BAD_REQUEST:
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
        if send_error is not None:
            # A timeout or connection error: the consumer redelivers, and the
            # devices that did get it collapse the repeat by its `tag`.
            raise send_error
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
