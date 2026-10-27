from datetime import UTC, datetime, timedelta

import pytest

from fanfan.presentation.web.festengine.signature import sign, verify_signature

pytestmark = pytest.mark.unit

# The example from the Standard Webhooks reference libraries' test suites.
SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"  # gitleaks:allow
MSG_ID = "msg_p5jXN8AQM9LWM0D4loKWxJek"
TIMESTAMP = 1614265330
BODY = b'{"test": 2432232314}'
SIGNATURE = "v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE="
SENT_AT = datetime.fromtimestamp(TIMESTAMP, UTC)


def _verify(
    signature_header: str | None,
    *,
    secret: str = SECRET,
    now: datetime = SENT_AT,
    timestamp: str | None = str(TIMESTAMP),
) -> bool:
    return verify_signature(
        secret,
        msg_id=MSG_ID,
        timestamp=timestamp,
        signature_header=signature_header,
        body=BODY,
        now=now,
    )


def test_sign_matches_the_reference_example() -> None:
    assert sign(SECRET, MSG_ID, TIMESTAMP, BODY) == SIGNATURE


def test_valid_signature_is_accepted() -> None:
    assert _verify(SIGNATURE)


def test_signature_under_another_key_is_rejected() -> None:
    other_secret = "whsec_" + "A" * 43 + "="
    assert not _verify(SIGNATURE, secret=other_secret)


@pytest.mark.parametrize("skew", [timedelta(minutes=-6), timedelta(minutes=6)])
def test_timestamp_outside_the_window_is_rejected(skew: timedelta) -> None:
    assert not _verify(SIGNATURE, now=SENT_AT + skew)


def test_any_matching_signature_among_several_is_accepted() -> None:
    assert _verify(f"v1,bm90LWl0 {SIGNATURE}")


@pytest.mark.parametrize("header", [None, "", "v1,", "v1,ŝ"])
def test_missing_or_garbage_signature_is_rejected(header: str | None) -> None:
    assert not _verify(header)


def test_non_numeric_timestamp_is_rejected() -> None:
    assert not _verify(SIGNATURE, timestamp="yesterday")
