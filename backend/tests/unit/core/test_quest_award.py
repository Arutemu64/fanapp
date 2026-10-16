from datetime import UTC, datetime, timedelta
from uuid import uuid7

import pytest

from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.quest import (
    CannotAwardSelf,
    QuestAwardAlreadyCancelled,
    QuestAwardAmountOutOfRange,
    QuestAwardCancelWindowExpired,
)
from fanfan.core.models.quest_award import QuestAward, format_points
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import UserId

pytestmark = pytest.mark.unit

NOW = datetime(2027, 3, 13, 12, 0, tzinfo=UTC)
WINDOW = timedelta(minutes=15)
PLAYER = UserId(uuid7())
VOLUNTEER = UserId(uuid7())
OTHER_VOLUNTEER = UserId(uuid7())


def _award(amount: int = 10) -> QuestAward:
    award = QuestAward.create(
        award_id=QuestAwardId(uuid7()),
        user_id=PLAYER,
        amount=amount,
        message="Нашёл Тоторо",
        awarded_by=VOLUNTEER,
        max_amount=100,
        now=NOW,
    )
    award.pull_events()
    return award


def test_create_notifies_the_player() -> None:
    award = QuestAward.create(
        award_id=QuestAwardId(uuid7()),
        user_id=PLAYER,
        amount=21,
        message="Нашёл Тоторо",
        awarded_by=VOLUNTEER,
        max_amount=100,
        now=NOW,
    )

    [event] = award.pull_events()

    assert isinstance(event, NotificationQueued)
    assert event.notification.user_id == PLAYER
    assert event.notification.title == "+21 балл в квесте"
    assert event.notification.type is NotificationType.QUEST


def test_create_refuses_awarding_yourself() -> None:
    with pytest.raises(CannotAwardSelf):
        QuestAward.create(
            award_id=QuestAwardId(uuid7()),
            user_id=VOLUNTEER,
            amount=10,
            message="Себе",
            awarded_by=VOLUNTEER,
            max_amount=100,
            now=NOW,
        )


@pytest.mark.parametrize("amount", [0, -5, 101])
def test_create_refuses_amount_outside_the_cap(amount: int) -> None:
    with pytest.raises(QuestAwardAmountOutOfRange):
        _award(amount)


def test_volunteer_cancels_own_award_within_the_window() -> None:
    award = _award()
    later = NOW + WINDOW - timedelta(seconds=1)

    award.cancel(
        by_user_id=VOLUNTEER, can_manage=False, cancel_window=WINDOW, now=later
    )

    assert award.cancelled_at == later
    assert award.cancelled_by == VOLUNTEER
    [event] = award.pull_events()
    assert isinstance(event, NotificationQueued)
    assert event.notification.title == "Начисление отменено"


def test_volunteer_cannot_cancel_after_the_window() -> None:
    award = _award()

    with pytest.raises(QuestAwardCancelWindowExpired):
        award.cancel(
            by_user_id=VOLUNTEER,
            can_manage=False,
            cancel_window=WINDOW,
            now=NOW + WINDOW,
        )


def test_volunteer_cannot_cancel_someone_elses_award() -> None:
    award = _award()

    with pytest.raises(AccessDenied):
        award.cancel(
            by_user_id=OTHER_VOLUNTEER, can_manage=False, cancel_window=WINDOW, now=NOW
        )


def test_manager_cancels_any_award_at_any_time() -> None:
    award = _award()

    award.cancel(
        by_user_id=OTHER_VOLUNTEER,
        can_manage=True,
        cancel_window=WINDOW,
        now=NOW + timedelta(days=1),
    )

    assert award.is_cancelled


def test_cancel_twice_is_refused() -> None:
    award = _award()
    award.cancel(by_user_id=VOLUNTEER, can_manage=True, cancel_window=WINDOW, now=NOW)

    with pytest.raises(QuestAwardAlreadyCancelled):
        award.cancel(
            by_user_id=VOLUNTEER, can_manage=True, cancel_window=WINDOW, now=NOW
        )


@pytest.mark.parametrize(
    ("amount", "expected"),
    [(1, "1 балл"), (3, "3 балла"), (5, "5 баллов"), (11, "11 баллов")],
)
def test_format_points(amount: int, expected: str) -> None:
    assert format_points(amount) == expected
