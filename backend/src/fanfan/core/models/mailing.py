from dataclasses import dataclass

from fanfan.core.events.notifications import BroadcastQueued, MailingCancelled
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    MailingNotCancellable,
)
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId, MailingStatus, generate_mailing_id
from fanfan.core.vo.user import UserId, UserRole


@dataclass(slots=True, kw_only=True)
class Mailing(AggregateRoot):
    id: MailingId
    status: MailingStatus
    by_user_id: UserId | None
    # Kept so a mailing survives its own fan-out: the per-user notifications get
    # deleted on cancel and purged by retention, so the mailing row is the only
    # durable record of what was sent. `body` is the exact broadcast text, or a
    # short change summary for a schedule fan-out (whose per-recipient texts are
    # templated variants of it). `roles` is None for a schedule fan-out — that is
    # not a role-targeted broadcast (recipients are derived: editors, announcement
    # opt-ins, event subscribers) — so it distinguishes the two mailing kinds.
    body: str | None
    roles: list[UserRole] | None

    @classmethod
    def create(cls, by_user_id: UserId) -> Mailing:
        return cls(
            id=generate_mailing_id(),
            status=MailingStatus.PENDING,
            by_user_id=by_user_id,
            body=None,
            roles=None,
        )

    def queue_broadcast(self, body: str, roles: list[UserRole]) -> None:
        # Persist what was sent on the mailing itself, then record the broadcast
        # as a domain event instead of publishing it directly. The UnitOfWork
        # writes the event to the outbox in the same transaction as this mailing,
        # so the row and its event are durable together (see docs/backend.md ->
        # Transactional outbox).
        self.body = body
        self.roles = roles
        self.record_event(BroadcastQueued(mailing_id=self.id, body=body, roles=roles))

    def start_sending(self) -> None:
        # Guard first: a mailing cancelled between creation and fan-out must not
        # flip back to an active state. Re-entrant from SENDING (the fan-out
        # trigger is redelivered at-least-once), so this is a no-op the 2nd time.
        self.ensure_active()
        self.status = MailingStatus.SENDING

    def mark_finished(self) -> None:
        self.status = MailingStatus.FINISHED

    def register_delivery(self, *, sent_count: int, total_count: int) -> bool:
        """Apply one unit of fan-out progress; return True iff it just finished.

        The completion rule ("finished once every queued notification exists")
        lives here, not in the persistence layer. The counts are not aggregate
        state — they are a high-write running total maintained by atomic,
        idempotent per-notification increments — so they are passed in. The
        caller holds the mailing row lock, which serializes this decision.
        """
        if self.status is not MailingStatus.SENDING:
            return False
        if total_count > 0 and sent_count >= total_count:
            self.mark_finished()
            return True
        return False

    def cancel(self) -> None:
        if self.status is MailingStatus.CANCELLED:
            raise MailingAlreadyCancelled
        # A mailing whose fan-out already completed (or failed) has nothing left
        # to stop — undelivered notifications are what cancellation removes, and
        # a delivered push/Telegram/VK message cannot be recalled anyway.
        if self.status in (MailingStatus.FINISHED, MailingStatus.FAILED):
            raise MailingNotCancellable
        self.status = MailingStatus.CANCELLED
        # The consumer of this event deletes the undelivered notifications and
        # confirms the CANCELLED status; recording it here (vs publishing) keeps
        # the status flip and the event in one transaction via the outbox.
        self.record_event(MailingCancelled(mailing_id=self.id))

    def ensure_active(self) -> None:
        if self.status is MailingStatus.CANCELLED:
            raise MailingAlreadyCancelled
