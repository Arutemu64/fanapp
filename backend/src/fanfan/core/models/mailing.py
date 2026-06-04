from dataclasses import dataclass

from fanfan.core.exceptions.notifications import MailingCancelled
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId, MailingStatus, generate_mailing_id
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Mailing(AggregateRoot):
    id: MailingId
    status: MailingStatus
    by_user_id: UserId | None

    @classmethod
    def create(cls, by_user_id: UserId) -> Mailing:
        return cls(
            id=generate_mailing_id(),
            status=MailingStatus.PENDING,
            by_user_id=by_user_id,
        )

    def set_as_cancelled(self) -> None:
        self.status = MailingStatus.CANCELLED

    def ensure_active(self) -> None:
        if self.status == MailingStatus.CANCELLED:
            raise MailingCancelled
