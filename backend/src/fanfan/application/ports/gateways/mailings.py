from typing import Protocol

from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.dto.page import CursorPagination
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId


class MailingGateway(Protocol):
    async def add(self, mailing: Mailing) -> None: ...
    # Row-locked unless lock is False; read unlocked where nothing is written
    # back, so a reader never queues behind the fan-out holding the row.
    async def get(
        self, mailing_id: MailingId, *, lock: bool = True
    ) -> Mailing | None: ...

    # Persists status, body and total_count of a mailing loaded with get().
    # sent_count is not written here: increment_sent owns it.
    async def save(self, mailing: Mailing) -> None: ...
    # Atomically add incr_by to sent_count; returns the post-increment
    # (sent_count, total_count) so the caller can decide completion.
    async def increment_sent(
        self, mailing_id: MailingId, incr_by: int
    ) -> tuple[int, int]: ...

    async def read_mailing(self, mailing_id: MailingId) -> MailingDTO | None: ...
    async def read_broadcasts(
        self, pagination: CursorPagination
    ) -> list[MailingDTO]: ...
