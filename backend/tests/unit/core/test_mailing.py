from uuid import uuid7

import pytest

from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingStatus
from fanfan.core.vo.user import UserId, UserRole

pytestmark = pytest.mark.unit


def test_mark_failed_fails_a_mailing_whose_fan_out_never_finished() -> None:
    # PENDING covers a fan-out that stored some notifications and then gave up.
    mailing = Mailing.create(by_user_id=UserId(uuid7()))

    mailing.mark_failed()

    assert mailing.status is MailingStatus.FAILED


@pytest.mark.parametrize("status", [MailingStatus.FINISHED, MailingStatus.CANCELLED])
def test_mark_failed_leaves_a_settled_mailing_alone(status: MailingStatus) -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))
    mailing.status = status

    mailing.mark_failed()

    assert mailing.status is status


def test_finish_records_the_recipient_count() -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))

    mailing.finish(3)

    assert mailing.total_count == 3
    assert mailing.status is MailingStatus.FINISHED


def test_finish_refuses_a_cancelled_mailing() -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))
    mailing.cancel()

    with pytest.raises(MailingAlreadyCancelled):
        mailing.finish(3)


@pytest.mark.parametrize(
    "status", [MailingStatus.PENDING, MailingStatus.FINISHED, MailingStatus.FAILED]
)
def test_cancel_recalls_a_mailing_in_any_uncancelled_status(
    status: MailingStatus,
) -> None:
    # FINISHED means stored, not delivered: its channel sends can still be
    # stopped, so a finished mailing is cancellable too.
    mailing = Mailing.create(by_user_id=UserId(uuid7()))
    mailing.status = status

    mailing.cancel()

    assert mailing.status is MailingStatus.CANCELLED


def test_cancel_refuses_a_cancelled_mailing() -> None:
    mailing = Mailing.create(by_user_id=UserId(uuid7()))
    mailing.cancel()

    with pytest.raises(MailingAlreadyCancelled):
        mailing.cancel()


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
    mailing.body = "Сдвиг расписания"

    assert not mailing.is_broadcast(
        by_user_id=author, body="Сдвиг расписания", roles=[]
    )
