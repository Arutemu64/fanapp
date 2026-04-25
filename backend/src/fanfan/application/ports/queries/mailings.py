from typing import Protocol

from fanfan.application.dto.mailing import MailingDTO
from fanfan.core.vo.mailing import MailingId


class MailingQuery(Protocol):
    async def read_mailing(self, mailing_id: MailingId) -> MailingDTO | None: ...
