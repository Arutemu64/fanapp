from datetime import datetime

from pydantic import BaseModel, Field

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.user import UserId


class NotificationDTO(BaseModel):
    id: NotificationId
    # The recipient: routes the realtime publish. Kept out of the API, where it
    # is always the caller.
    user_id: UserId = Field(exclude=True)
    title: str
    body: str
    type: NotificationType
    # In-app deep-link path; None falls back to the app root on click.
    path: str | None
    mailing_id: MailingId | None
    created_at: datetime
    seen_at: datetime | None
