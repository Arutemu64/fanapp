from uuid import uuid7

import pytest

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
