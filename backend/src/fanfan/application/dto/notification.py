from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.user import UserId


class NotificationDTO(BaseModel):
    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    # In-app deep-link path; None falls back to the app root on click.
    path: str | None
    mailing_id: MailingId | None
    created_at: datetime
    seen_at: datetime | None


class RealtimeNotificationDTO(BaseModel):
    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    # In-app deep-link path; None falls back to the app root on click.
    path: str | None
    mailing_id: MailingId | None
    created_at: datetime
    seen_at: datetime | None
