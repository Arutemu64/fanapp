from typing import ClassVar

from fanfan.core.dto.notification import NewNotificationDTO
from fanfan.core.events.base import AppEvent
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.user import UserRole


class NewNotificationEvent(AppEvent):
    subject: ClassVar[str] = "notifications.new"

    notification: NewNotificationDTO


class CreatedNotificationEvent(AppEvent):
    subject: ClassVar[str] = "notifications.created"

    notification_id: NotificationId


class NewRolesNotificationEvent(AppEvent):
    subject: ClassVar[str] = "notifications.roles.new"

    title: str
    body: str
    roles: list[UserRole]
    mailing_id: MailingId


class CancelMailingEvent(AppEvent):
    subject: ClassVar[str] = "notification.mailing.cancel"

    mailing_id: MailingId
