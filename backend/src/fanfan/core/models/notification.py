from dataclasses import dataclass
from datetime import datetime

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Notification(AggregateRoot):
    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    mailing_id: MailingId | None
    seen_at: datetime | None


@dataclass(slots=True, kw_only=True)
class NewNotification:
    """Data required to create a Notification.

    Carried by the NotificationQueued service event and consumed by the
    CreateNotification interactor. Lives in core so the domain event does not
    depend on the application layer.
    """

    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    mailing_id: MailingId | None
