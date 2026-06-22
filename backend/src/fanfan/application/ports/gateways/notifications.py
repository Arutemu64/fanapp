from datetime import datetime
from typing import Protocol

from fanfan.application.dto.notification import NotificationDTO, RealtimeNotificationDTO
from fanfan.application.dto.page import Pagination
from fanfan.core.models.notification import Notification, NotificationRevocation
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.user import UserId


class NotificationGateway(Protocol):
    async def add(self, notification: Notification) -> None: ...
    async def get(self, notification_id: NotificationId) -> Notification | None: ...
    async def mark_all_read_for_user(
        self, user_id: UserId, timestamp: datetime
    ) -> None: ...
    async def delete_all_by_mailing_id(self, mailing_id: MailingId) -> None: ...

    async def set_telegram_message_id(
        self, notification_id: NotificationId, message_id: int
    ) -> None:
        """Record the Telegram message id of a delivered notification.

        Stored so the message can later be deleted when the mailing is recalled.
        """
        ...

    async def read_revocations_by_mailing_id(
        self, mailing_id: MailingId
    ) -> list[NotificationRevocation]: ...

    async def delete_created_before(self, days: int) -> int:
        """Delete notifications older than ``days``; return the row count."""
        ...

    # Read projections (return DTOs, not aggregates)
    async def read_realtime_notification(
        self, notification_id: NotificationId
    ) -> RealtimeNotificationDTO | None: ...

    async def read_list_user_notifications(
        self, user_id: UserId, pagination: Pagination
    ) -> list[NotificationDTO]: ...
