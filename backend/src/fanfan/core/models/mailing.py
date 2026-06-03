from dataclasses import dataclass

from fanfan.core.exceptions.notifications import MailingCancelled
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Mailing(AggregateRoot):
    id: MailingId
    status: MailingStatus
    by_user_id: UserId | None

    sent_count: int
    total_count: int

    def update_total(self, total: int) -> None:
        self.total_count = total

    def set_as_cancelled(self) -> None:
        self.status = MailingStatus.CANCELLED

    def ensure_active(self) -> None:
        if self.status == MailingStatus.CANCELLED:
            raise MailingCancelled
