from typing import ClassVar

from fanfan.core.events.base import DomainEvent
from fanfan.core.vo.notification import NotificationId


class NotificationCreated(DomainEvent):
    subject: ClassVar[str] = "notifications.created"

    notification_id: NotificationId

    def dedup_id(self) -> str:
        return f"{self.subject}:{self.notification_id}"
