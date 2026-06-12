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
    # In-app path the notification deep-links to (e.g. "/schedule"). Consumed by
    # the web UI (clickable list items/toasts) and the push service worker, which
    # navigates here on notification click. None falls back to the app root.
    path: str | None
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
    # In-app deep-link path; see Notification.path above. None falls back to root.
    path: str | None
    mailing_id: MailingId | None
