from dataclasses import dataclass

from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId, MailingStatus, generate_mailing_id
from fanfan.core.vo.user import UserId, UserRole


@dataclass(slots=True, kw_only=True)
class Mailing(AggregateRoot):
    id: MailingId
    status: MailingStatus
    by_user_id: UserId | None
    body: str | None
    roles: list[UserRole] | None
    total_count: int

    @classmethod
    def create(cls, by_user_id: UserId, mailing_id: MailingId | None = None) -> Mailing:
        if mailing_id is None:
            mailing_id = generate_mailing_id()
        return cls(
            id=mailing_id,
            status=MailingStatus.PENDING,
            by_user_id=by_user_id,
            body=None,
            roles=None,
            total_count=0,
        )

    def queue_broadcast(self, body: str, roles: list[UserRole]) -> None:
        self.body = body
        self.roles = roles

    def is_broadcast(
        self, by_user_id: UserId, body: str, roles: list[UserRole]
    ) -> bool:
        """Whether this mailing is that broadcast, so a retry can replay it.

        Roles compare as a set: the audience is the same whatever order the
        client listed it in.
        """
        if self.by_user_id != by_user_id or self.body != body:
            return False
        if self.roles is None:
            return False
        return set(self.roles) == set(roles)

    def finish(self, total_count: int) -> None:
        """Close the fan-out once it has stored every recipient's notification.

        Called in the transaction that stores the last batch, so FINISHED means
        every notification exists; the channel sends may still be going out.
        Idempotent: a redelivered fan-out stores nothing new and finishes again.
        """
        self.ensure_active()
        self.total_count = total_count
        self.status = MailingStatus.FINISHED

    def mark_failed(self) -> None:
        if self.status is not MailingStatus.PENDING:
            return
        self.status = MailingStatus.FAILED

    def cancel(self) -> None:
        if self.status is MailingStatus.CANCELLED:
            raise MailingAlreadyCancelled
        self.status = MailingStatus.CANCELLED

    def confirm_cancelled(self) -> None:
        """Settle a cancellation the consumer is reacting to; idempotent.

        Unlike cancel(), this never raises: CancelMailingCommand is delivered
        at-least-once, so a redelivery finds the mailing already CANCELLED.
        """
        self.status = MailingStatus.CANCELLED

    def ensure_active(self) -> None:
        if self.status is MailingStatus.CANCELLED:
            raise MailingAlreadyCancelled
