from dataclasses import dataclass
from datetime import datetime, timedelta

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import (
    SCHEDULE_NOTIFICATION_LIFETIME,
    NotificationId,
    NotificationType,
)
from fanfan.core.vo.schedule_entry import ScheduleEntryId
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
    # The act a subscription notice is about, so each act keeps its own push
    # lane and a notice about one never replaces a notice about another.
    event_id: ScheduleEntryId | None = None
    # Set once stored; None on a notification not yet inserted.
    created_at: datetime | None = None

    def remaining_lifetime(self, now: datetime) -> timedelta | None:
        """How much longer this notification stays true; None if it never ages.

        Only schedule notifications age: they describe the programme at the
        moment they were built. Everything else is as true late as on time.
        """
        if not self.type.is_schedule:
            return None
        if self.created_at is None:
            return SCHEDULE_NOTIFICATION_LIFETIME
        return SCHEDULE_NOTIFICATION_LIFETIME - (now - self.created_at)

    def is_stale(self, now: datetime) -> bool:
        """Whether delivering this notification now would mislead its reader."""
        remaining = self.remaining_lifetime(now)
        if remaining is None:
            return False
        return remaining < timedelta(0)


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
    # See Notification.event_id above.
    event_id: ScheduleEntryId | None = None
