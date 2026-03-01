from pydantic import BaseModel

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserId


class MailingDTO(BaseModel):
    id: MailingId
    total: int
    is_cancelled: bool
    by_user_id: UserId | None
