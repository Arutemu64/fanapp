from typing import ClassVar

from fanfan.core.events.base import AppEvent
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.user import UserRole


class NotificationQueued(AppEvent):
    subject: ClassVar[str] = "notifications.queued"

    notification: NewNotification


class NotificationCreated(AppEvent):
    subject: ClassVar[str] = "notifications.created"

    notification_id: NotificationId


class BroadcastQueued(AppEvent):
    subject: ClassVar[str] = "notifications.broadcast.queued"

    mailing_id: MailingId
    body: str
    roles: list[UserRole]


class MailingCancelled(AppEvent):
    subject: ClassVar[str] = "notifications.mailing.cancelled"

    mailing_id: MailingId
