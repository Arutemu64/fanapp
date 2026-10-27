import json
from uuid import uuid4, uuid7

import pytest
from pydantic import ValidationError

from fanfan.application.interactors.notifications.send_broadcast import (
    BROADCAST_BODY_MAX_LENGTH,
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


BODY_BYTE_BUDGET = 3002


def _with_body(body: str) -> SendBroadcastInput:
    return SendBroadcastInput(
        mailing_id=MailingId(uuid7()), body=body, roles=[UserRole.VISITOR]
    )


@pytest.mark.parametrize("unit", ["ж", "🎉", '"', "\x01"])
def test_longest_accepted_body_fits_the_push_payload(unit: str) -> None:
    count = BROADCAST_BODY_MAX_LENGTH // (len(unit.encode("utf-16-le")) // 2)
    body = _with_body(unit * count).body

    assert len(json.dumps(body).encode()) <= BODY_BYTE_BUDGET


def test_emoji_count_double_against_the_cap() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _with_body("🎉" * (BROADCAST_BODY_MAX_LENGTH // 2 + 1))

    [error] = exc_info.value.errors()
    assert error["type"] == "string_too_long"
    assert error["ctx"] == {"max_length": BROADCAST_BODY_MAX_LENGTH}
