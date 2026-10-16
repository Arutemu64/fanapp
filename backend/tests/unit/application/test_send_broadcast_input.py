from uuid import uuid4, uuid7

import pytest
from pydantic import ValidationError

from fanfan.application.interactors.notifications.send_broadcast import (
    SendBroadcastInput,
)
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole

pytestmark = pytest.mark.unit


def test_accepts_a_v7_mailing_id() -> None:
    mailing_id = MailingId(uuid7())

    data = SendBroadcastInput(
        mailing_id=mailing_id, body="Привет", roles=[UserRole.VISITOR]
    )

    assert data.mailing_id == mailing_id


def test_rejects_a_mailing_id_of_another_version() -> None:
    with pytest.raises(ValidationError):
        SendBroadcastInput(
            mailing_id=MailingId(uuid4()), body="Привет", roles=[UserRole.VISITOR]
        )
