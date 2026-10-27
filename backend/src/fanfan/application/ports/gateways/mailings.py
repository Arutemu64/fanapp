from typing import Protocol

from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.dto.page import CursorPagination
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId


class MailingGateway(Protocol):
    async def add(self, mailing: Mailing) -> None: ...
    async def get(
        self, mailing_id: MailingId, *, lock: bool = True
    ) -> Mailing | None: ...

    async def save(self, mailing: Mailing) -> None: ...

    async def read_broadcasts(
        self, pagination: CursorPagination
    ) -> list[MailingDTO]: ...
