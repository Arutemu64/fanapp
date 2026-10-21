from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from fanfan.application.dto.notification import NotificationDTO
from fanfan.application.dto.page import CursorPagination
from fanfan.core.models.notification import Notification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.user import UserId


class NotificationGateway(Protocol):
    async def add_many(self, notifications: Sequence[Notification]) -> int:
        """Insert the notifications in one statement; return how many were new.

        A notification whose id already exists is skipped, so a rerun fan-out
        inserts nothing twice and the count tells it how much was new.
        """
        ...

    async def get(
        self, notification_id: NotificationId, *, lock: bool = True
    ) -> Notification | None:
        """Load the notification, row-locked unless ``lock`` is False.

        Read without the lock where nothing is written back, so a slow reader
        cannot hold up the writers.
        """
        ...

    async def mark_all_read_for_user(
        self, user_id: UserId, timestamp: datetime
    ) -> None: ...
    async def mark_read_for_user(
        self,
        user_id: UserId,
        notification_ids: list[NotificationId],
        timestamp: datetime,
    ) -> None: ...
    async def count_unread_for_user(self, user_id: UserId) -> int: ...
    async def delete_all_by_mailing_id(self, mailing_id: MailingId) -> None: ...

    async def delete_created_before(self, days: int) -> int:
        """Delete notifications older than ``days``; return the row count."""
        ...

    async def read_realtime_notifications(
        self, notification_ids: Sequence[NotificationId]
    ) -> list[NotificationDTO]: ...

    async def read_list_user_notifications(
        self, user_id: UserId, pagination: CursorPagination
    ) -> list[NotificationDTO]: ...
