import asyncio
import base64
import html
import logging
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import override

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
from fanfan.core.vo.notification import NotificationType
from fanfan.presentation.web.config import WebConfig

logger = logging.getLogger(__name__)

_GONE_STATUS_CODES = frozenset({404, 410})
_CHANNEL_UNAVAILABLE_STATUS_CODES = frozenset({400, 401, 403})

_RETRY_AFTER_DEFAULT_SECONDS = 5

_DEFAULT_TTL = timedelta(hours=1)

_TOPIC_TAGS: dict[NotificationType, str] = {
    NotificationType.SCHEDULE_CHANGE: "schedule",
    NotificationType.SCHEDULE_SUBSCRIPTION: "subscription",
    NotificationType.BROADCAST: "broadcast",
}


def _topic_for(notification: Notification) -> str | None:
    if (
        notification.type is NotificationType.SCHEDULE_SUBSCRIPTION
        and notification.event_id is not None
    ):
        event_key = base64.urlsafe_b64encode(notification.event_id.bytes)
        return "sub" + event_key.decode().rstrip("=")
    return _TOPIC_TAGS.get(notification.type)


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
        text = text.replace("<br>", "\n")
        return html.unescape(nh3.clean(text, tags=set()))

    def _build_message_data(self, notification: Notification) -> MessageData:
        topic = _topic_for(notification)
        return {
            "web_push": 8030,
            "mutable": True,
            "notification": {
                "title": self._sanitize_text(notification.title),
                "body": self._sanitize_text(notification.body),
                "navigate": self.web_config.build_url(notification.path or "/"),
                "tag": topic or str(notification.id),
                "renotify": topic is not None,
                "data": {"test": notification.type == NotificationType.TEST},
            },
        }

    async def _send_to_devices(
        self, notification: Notification, push_subs: list[PushSubscription]
    ) -> list[httpx2.Response | BaseException]:
        message_data = self._build_message_data(notification)
        topic = _topic_for(notification)
        ttl = _DEFAULT_TTL
        remaining = notification.remaining_lifetime(datetime.now(UTC))
        if remaining is not None:
            ttl = max(remaining, timedelta(0))
        urgency: PushUrgency = "normal"
        if notification.type.is_time_sensitive:
            urgency = "high"
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

    @override
    async def send_notification(self, notification: Notification) -> None:
        self.client.ensure_available()
        push_subs = await self.push_sub_gateway.list_by_user(notification.user_id)
        await self.uow.commit()
        responses = await self._send_to_devices(notification, push_subs)
        retry_after: int | None = None
        send_error: BaseException | None = None
        for sub, response in zip(push_subs, responses, strict=True):
            if isinstance(response, BaseException):
                send_error = send_error or response
                continue
            response_retry_after = await self._handle_response(
                notification, sub, response
            )
            if response_retry_after is not None:
                retry_after = response_retry_after
        if send_error is not None:
            raise send_error
        if retry_after is not None:
            raise NotificationRetryAfter(retry_after=retry_after)

    async def _handle_response(
        self,
        notification: Notification,
        sub: PushSubscription,
        response: httpx2.Response,
    ) -> int | None:
        """Act on one device's response; return seconds to wait if throttled."""
        status_code = response.status_code
        if status_code in _GONE_STATUS_CODES:
            await self.push_sub_gateway.delete(sub)
            await self.uow.commit()
        elif status_code in _CHANNEL_UNAVAILABLE_STATUS_CODES:
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
            retry_after = self._retry_after_seconds(response)
            logger.warning(
                "Push service throttled or failed; will retry",
                extra={
                    "notification_id": str(notification.id),
                    "status_code": status_code,
                    "retry_after": retry_after,
                },
            )
            return retry_after
        elif status_code >= HTTPStatus.BAD_REQUEST:
            logger.warning(
                "Unexpected push service status",
                extra={
                    "notification_id": str(notification.id),
                    "status_code": status_code,
                },
            )
        return None

    @staticmethod
    def _retry_after_seconds(response: httpx2.Response) -> int:
        raw = response.headers.get("Retry-After")
        if raw is not None:
            try:
                parsed = int(raw)
            except ValueError:
                parsed = 0
            if parsed > 0:
                return parsed
        return _RETRY_AFTER_DEFAULT_SECONDS
