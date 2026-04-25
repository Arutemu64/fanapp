from typing import Protocol

from fanfan.application.dto.notification import NotificationDTO, RealtimeNotificationDTO
from fanfan.application.dto.page import Pagination
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.user import UserId


class NotificationQuery(Protocol):
    async def read_realtime_notification(
        self, notification_id: NotificationId
    ) -> RealtimeNotificationDTO | None: ...

    async def read_list_user_notifications(
        self, user_id: UserId, pagination: Pagination
    ) -> list[NotificationDTO]: ...
