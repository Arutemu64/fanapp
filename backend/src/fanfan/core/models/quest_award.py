from dataclasses import dataclass
from datetime import datetime, timedelta

from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.exceptions.base import AccessDenied, AppException
from fanfan.core.exceptions.quest import (
    CannotAwardSelf,
    QuestAwardAlreadyCancelled,
    QuestAwardAmountOutOfRange,
    QuestAwardCancelWindowExpired,
)
from fanfan.core.models.base import AggregateRoot
from fanfan.core.models.notification import NewNotification
from fanfan.core.utils.pluralize import Plurals, pluralize
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import UserId

QUEST_PATH = "/profile/quest"
_POINTS = Plurals("балл", "балла", "баллов")


def format_points(amount: int) -> str:
    return f"{amount} {pluralize(amount, _POINTS)}"


@dataclass(slots=True, kw_only=True)
class QuestAward(AggregateRoot):
    """One entry in the quest points ledger (docs/adr/0035).

    A player's balance is the sum of their awards that are not cancelled.
    Cancelling marks the row instead of deleting it, so a dispute over who
    gave or took back points can always be settled from the ledger.
    """

    id: QuestAwardId
    user_id: UserId
    amount: int
    message: str
    # None once the staff account that gave the award is deleted.
    awarded_by: UserId | None
    created_at: datetime
    cancelled_at: datetime | None = None
    cancelled_by: UserId | None = None

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        *,
        award_id: QuestAwardId,
        user_id: UserId,
        amount: int,
        message: str,
        awarded_by: UserId,
        max_amount: int,
        now: datetime,
    ) -> QuestAward:
        if user_id == awarded_by:
            raise CannotAwardSelf
        if not 1 <= amount <= max_amount:
            raise QuestAwardAmountOutOfRange
        award = cls(
            id=award_id,
            user_id=user_id,
            amount=amount,
            message=message,
            awarded_by=awarded_by,
            created_at=now,
        )
        award.record_event(
            NotificationQueued(
                notification=NewNotification(
                    id=generate_notification_id(),
                    user_id=user_id,
                    title=f"+{format_points(amount)}",
                    body=message,
                    type=NotificationType.QUEST,
                    path=QUEST_PATH,
                    mailing_id=None,
                )
            )
        )
        return award

    def is_same_award(
        self, *, user_id: UserId, amount: int, message: str, awarded_by: UserId
    ) -> bool:
        return (
            self.user_id == user_id
            and self.amount == amount
            and self.message == message
            and self.awarded_by == awarded_by
        )

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled_at is not None

    def cancel(
        self,
        *,
        by_user_id: UserId,
        can_manage: bool,
        cancel_window: timedelta,
        now: datetime,
    ) -> None:
        refusal = cancel_refusal(
            awarded_by=self.awarded_by,
            created_at=self.created_at,
            cancelled_at=self.cancelled_at,
            by_user_id=by_user_id,
            can_manage=can_manage,
            cancel_window=cancel_window,
            now=now,
        )
        if refusal is not None:
            raise refusal
        self.cancelled_at = now
        self.cancelled_by = by_user_id
        self.record_event(
            NotificationQueued(
                notification=NewNotification(
                    id=generate_notification_id(),
                    user_id=self.user_id,
                    title="Начисление отменено",
                    body=f"−{format_points(self.amount)}: {self.message}",
                    type=NotificationType.QUEST,
                    path=QUEST_PATH,
                    mailing_id=None,
                )
            )
        )


def cancel_refusal(  # noqa: PLR0913
    *,
    awarded_by: UserId | None,
    created_at: datetime,
    cancelled_at: datetime | None,
    by_user_id: UserId,
    can_manage: bool,
    cancel_window: timedelta,
    now: datetime,
) -> AppException | None:
    """Why ``by_user_id`` may not cancel this award, or None if they may.

    One rule for both the cancel itself and the award list's cancel button, so
    the button never offers what the server then refuses.
    """
    if cancelled_at is not None:
        return QuestAwardAlreadyCancelled()
    # Organizers settle disputes at any time; a volunteer may only undo their
    # own slip shortly after making it, so points a player has already counted
    # on do not vanish hours later.
    if can_manage:
        return None
    if by_user_id != awarded_by:
        return AccessDenied()
    if now >= created_at + cancel_window:
        return QuestAwardCancelWindowExpired()
    return None
