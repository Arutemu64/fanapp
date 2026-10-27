from datetime import datetime

from pydantic import BaseModel

from fanfan.application.dto.user import UserRefDTO
from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserRole


class MailingDTO(BaseModel):
    id: MailingId
    status: MailingStatus
    created_by: UserRefDTO | None
    body: str | None
    # Empty for a mailing that isn't a broadcast (schedule-change announcements).
    roles: list[UserRole]
    total_count: int
    created_at: datetime
