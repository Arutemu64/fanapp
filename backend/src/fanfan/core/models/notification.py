from dataclasses import dataclass
from datetime import datetime
from typing import Self

from fanfan.core.events.notifications import NotificationCreated
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
    # In-app path the notification deep-links to (e.g. "/schedule"). Consumed by
    # the web UI (clickable list items/toasts) and the push service worker, which
    # navigates here on notification click. None falls back to the app root.
    path: str | None
    mailing_id: MailingId | None
    seen_at: datetime | None

    @classmethod
    def create(cls, new: NewNotification) -> Self:
        instance = cls(
            id=new.id,
            user_id=new.user_id,
            title=new.title,
            body=new.body,
            type=new.type,
            path=new.path,
            mailing_id=new.mailing_id,
            seen_at=None,
        )
        instance.record_event(NotificationCreated(notification_id=instance.id))
        return instance


@dataclass(slots=True, kw_only=True)
class NewNotification:
    """Data required to create a Notification.

    Carried by CreateNotificationCommand and consumed by the CreateNotification
    interactor. Lives in core so an aggregate can build its own notification
    (QuestAward.award_notification).
    """

    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    # In-app deep-link path; see Notification.path above. None falls back to root.
    path: str | None
    mailing_id: MailingId | None
