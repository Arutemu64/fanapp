from dataclasses import dataclass, field
from uuid import uuid7

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Mailing:
    id: MailingId = field(default_factory=uuid7)
    total: int
    is_cancelled: bool
    by_user_id: UserId | None

    def update_total(self, total: int) -> None:
        self.total = total

    def set_as_cancelled(self) -> None:
        self.is_cancelled = True
