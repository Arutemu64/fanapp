from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserId, UserRole


class MailingDTO(BaseModel):
    id: MailingId
    status: MailingStatus
    by_user_id: UserId | None
    body: str | None
    roles: list[UserRole] | None
    sent_count: int
    total_count: int
    created_at: datetime
