from dataclasses import dataclass
from datetime import datetime

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Notification:
    id: NotificationId
    user_id: UserId
    title: str
    body: str
    type: NotificationType
    mailing_id: MailingId | None
    seen_at: datetime | None
