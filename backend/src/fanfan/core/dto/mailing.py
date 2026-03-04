from pydantic import BaseModel

from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserId


class MailingDTO(BaseModel):
    id: MailingId
    status: MailingStatus
    by_user_id: UserId | None
    sent_count: int
    total_count: int
