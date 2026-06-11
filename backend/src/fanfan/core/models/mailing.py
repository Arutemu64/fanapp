from dataclasses import dataclass

from fanfan.core.events.notifications import BroadcastQueued
from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId, MailingStatus, generate_mailing_id
from fanfan.core.vo.user import UserId, UserRole


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

    def queue_broadcast(self, body: str, roles: list[UserRole]) -> None:
        # Record the broadcast as a domain event instead of publishing it
        # directly. The UnitOfWork writes it to the outbox in the same
        # transaction as this mailing, so the row and its event are durable
        # together (see docs/backend.md -> Transactional outbox).
        self.record_event(BroadcastQueued(mailing_id=self.id, body=body, roles=roles))

    def set_as_cancelled(self) -> None:
        self.status = MailingStatus.CANCELLED

    def ensure_active(self) -> None:
        if self.status == MailingStatus.CANCELLED:
            raise MailingAlreadyCancelled
