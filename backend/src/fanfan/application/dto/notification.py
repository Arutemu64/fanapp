from datetime import datetime
from uuid import uuid7

from pydantic import BaseModel, Field

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.user import UserId


class NewNotificationDTO(BaseModel):
    id: NotificationId = Field(default_factory=uuid7)
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    mailing_id: MailingId | None


class NotificationDTO(BaseModel):
    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    mailing_id: MailingId | None
    created_at: datetime
    seen_at: datetime | None


class RealtimeNotificationDTO(BaseModel):
    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    mailing_id: MailingId | None
    created_at: datetime
    seen_at: datetime | None
