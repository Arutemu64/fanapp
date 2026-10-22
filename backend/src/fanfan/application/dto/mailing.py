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
    roles: list[UserRole] | None
    total_count: int
    created_at: datetime
