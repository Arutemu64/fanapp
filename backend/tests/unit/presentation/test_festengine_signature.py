import time

import pytest
from pydantic import SecretStr, ValidationError

from fanfan.presentation.web.festengine import (
    FestEngineConfig,
    SignedRequest,
    sign,
    verify_signature,
)

pytestmark = pytest.mark.unit

# The worked example from the Standard Webhooks spec README.
SPEC_SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"
SPEC_MSG_ID = "msg_p5jXN8AQM9LWM0D4loKWxJek"
SPEC_TIMESTAMP = "1614265330"
SPEC_BODY = b'{"test": 2432232314}'
SPEC_SIGNATURE = "v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE="
SPEC_NOW = float(SPEC_TIMESTAMP)


def _request(
    signatures: str | None = SPEC_SIGNATURE,
    timestamp: str | None = SPEC_TIMESTAMP,
) -> SignedRequest:
    return SignedRequest(
        msg_id=SPEC_MSG_ID,
        timestamp=timestamp,
        signatures=signatures,
        body=SPEC_BODY,
    )


def test_sign_matches_the_spec_example() -> None:
    assert sign(SPEC_SECRET, SPEC_MSG_ID, SPEC_TIMESTAMP, SPEC_BODY) == SPEC_SIGNATURE


def test_sign_accepts_a_secret_without_the_prefix() -> None:
    bare = SPEC_SECRET.removeprefix("whsec_")
    assert sign(bare, SPEC_MSG_ID, SPEC_TIMESTAMP, SPEC_BODY) == SPEC_SIGNATURE


def test_valid_signature_is_accepted() -> None:
    assert verify_signature(SPEC_SECRET, _request(), now=SPEC_NOW)


def test_wrong_key_is_rejected() -> None:
    other_secret = "whsec_" + "A" * 32
    assert not verify_signature(other_secret, _request(), now=SPEC_NOW)


def test_tampered_body_is_rejected() -> None:
    request = SignedRequest(
        msg_id=SPEC_MSG_ID,
        timestamp=SPEC_TIMESTAMP,
        signatures=SPEC_SIGNATURE,
        body=b'{"test": 1}',
    )
    assert not verify_signature(SPEC_SECRET, request, now=SPEC_NOW)


@pytest.mark.parametrize("offset", [-301, 301])
def test_timestamp_outside_five_minutes_is_rejected(offset: int) -> None:
    assert not verify_signature(SPEC_SECRET, _request(), now=SPEC_NOW + offset)


@pytest.mark.parametrize("offset", [-300, 300])
def test_timestamp_at_the_window_edge_is_accepted(offset: int) -> None:
    assert verify_signature(SPEC_SECRET, _request(), now=SPEC_NOW + offset)


def test_any_of_several_signatures_may_match() -> None:
    signatures = f"v1,bm90LXRoaXMtb25l {SPEC_SIGNATURE}"
    assert verify_signature(SPEC_SECRET, _request(signatures), now=SPEC_NOW)


def test_signature_with_another_version_is_rejected() -> None:
    other_version = SPEC_SIGNATURE.replace("v1,", "v1a,")
    assert not verify_signature(SPEC_SECRET, _request(other_version), now=SPEC_NOW)


@pytest.mark.parametrize(
    "request_",
    [
        _request(signatures=None),
        _request(timestamp=None),
        _request(timestamp="not-a-number"),
    ],
)
def test_missing_or_malformed_headers_are_rejected(request_: SignedRequest) -> None:
    assert not verify_signature(SPEC_SECRET, request_, now=SPEC_NOW)


def test_config_rejects_a_secret_that_is_not_base64() -> None:
    with pytest.raises(ValidationError):
        FestEngineConfig(webhook_secret=SecretStr("whsec_not base64!"))


def test_config_defaults_to_disabled() -> None:
    assert FestEngineConfig().webhook_secret is None


def test_signature_verifies_with_the_reference_library() -> None:
    standardwebhooks = pytest.importorskip("standardwebhooks")
    # The library checks the timestamp against its own clock, so use a fresh one.
    timestamp = str(int(time.time()))
    headers = {
        "webhook-id": SPEC_MSG_ID,
        "webhook-timestamp": timestamp,
        "webhook-signature": sign(SPEC_SECRET, SPEC_MSG_ID, timestamp, SPEC_BODY),
    }
    standardwebhooks.Webhook(SPEC_SECRET).verify(SPEC_BODY, headers)
