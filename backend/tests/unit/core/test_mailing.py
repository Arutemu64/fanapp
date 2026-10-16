from uuid import uuid7

import pytest

from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingStatus
from fanfan.core.vo.user import UserId, UserRole

pytestmark = pytest.mark.unit


def test_mark_failed_fails_a_mailing_that_never_started() -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))

    mailing.mark_failed()

    assert mailing.status is MailingStatus.FAILED


@pytest.mark.parametrize(
    "status",
    [MailingStatus.SENDING, MailingStatus.FINISHED, MailingStatus.CANCELLED],
)
def test_mark_failed_leaves_a_started_or_settled_mailing_alone(
    status: MailingStatus,
) -> None:
    # Once SENDING, notifications may already be out and the fan-out owns the
    # mailing; a settled one must not be relabelled.
    mailing = Mailing.create(by_user_id=UserId(uuid7()))
    mailing.status = status

    mailing.mark_failed()

    assert mailing.status is status


def test_begin_fan_out_with_recipients_starts_sending() -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))

    mailing.begin_fan_out(3)

    assert mailing.total_count == 3
    assert mailing.status is MailingStatus.SENDING


def test_begin_fan_out_without_recipients_finishes_at_once() -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))

    mailing.begin_fan_out(0)

    assert mailing.total_count == 0
    assert mailing.status is MailingStatus.FINISHED


def test_begin_fan_out_refuses_a_cancelled_mailing() -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))
    mailing.cancel()

    with pytest.raises(MailingAlreadyCancelled):
        mailing.begin_fan_out(3)


def test_confirm_cancelled_is_idempotent() -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))
    mailing.cancel()

    mailing.confirm_cancelled()

    assert mailing.status is MailingStatus.CANCELLED


def test_is_broadcast_matches_the_same_author_text_and_audience() -> None:
    author = UserId(uuid7())
    mailing = Mailing.create(by_user_id=author)
    mailing.queue_broadcast(body="Привет", roles=[UserRole.VISITOR, UserRole.VOLUNTEER])

    # The audience is a set: a retry that lists the roles in another order is
    # still the same broadcast.
    assert mailing.is_broadcast(
        by_user_id=author, body="Привет", roles=[UserRole.VOLUNTEER, UserRole.VISITOR]
    )


@pytest.mark.parametrize(
    ("same_author", "body", "roles"),
    [
        (False, "Привет", [UserRole.VISITOR]),
        (True, "Пока", [UserRole.VISITOR]),
        (True, "Привет", [UserRole.ORGANIZER]),
    ],
)
def test_is_broadcast_rejects_a_different_broadcast(
    *, same_author: bool, body: str, roles: list[UserRole]
) -> None:
    author = UserId(uuid7())
    mailing = Mailing.create(by_user_id=author)
    mailing.queue_broadcast(body="Привет", roles=[UserRole.VISITOR])
    caller = author if same_author else UserId(uuid7())

    assert not mailing.is_broadcast(by_user_id=caller, body=body, roles=roles)


def test_is_broadcast_rejects_a_change_announcement() -> None:
    author = UserId(uuid7())
    mailing = Mailing.create(by_user_id=author)
    mailing.record_summary("Сдвиг расписания")

    assert not mailing.is_broadcast(
        by_user_id=author, body="Сдвиг расписания", roles=[]
    )
