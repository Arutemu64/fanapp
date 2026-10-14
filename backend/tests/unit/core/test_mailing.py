from uuid import uuid7

import pytest

from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingStatus
from fanfan.core.vo.user import UserId

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
