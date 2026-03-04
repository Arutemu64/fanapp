from dataclasses import dataclass, field
from uuid import uuid7

from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Mailing:
    id: MailingId = field(default_factory=uuid7)
    status: MailingStatus
    by_user_id: UserId | None

    sent_count: int
    total_count: int

    def update_total(self, total: int) -> None:
        self.total_count = total

    def set_as_cancelled(self) -> None:
        self.status = MailingStatus.CANCELLED
