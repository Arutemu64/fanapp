from dataclasses import dataclass
from datetime import datetime

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import (
    SCHEDULE_NOTIFICATION_LIFETIME,
    NotificationId,
    NotificationType,
)
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
    # Set once stored; None on a notification not yet inserted.
    created_at: datetime | None = None

    def is_stale(self, now: datetime) -> bool:
        """Whether delivering this notification now would mislead its reader.

        Only schedule notifications go stale: they describe the programme at the
        moment they were built. Everything else is as true late as on time.
        """
        if self.created_at is None or not self.type.is_schedule:
            return False
        return now - self.created_at > SCHEDULE_NOTIFICATION_LIFETIME


@dataclass(slots=True, kw_only=True)
class NewNotification:
    """Data required to create a Notification.

    Carried by CreateNotificationCommand, built in bulk by the fan-outs, and
    stored by NotificationFanOut. Lives in core so an aggregate can build its
    own notification (QuestAward.award_notification).
    """

    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    # In-app deep-link path; see Notification.path above. None falls back to root.
    path: str | None
    mailing_id: MailingId | None
