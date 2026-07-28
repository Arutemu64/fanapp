import pytest
from authlib.integrations.starlette_client import OAuthError

from fanfan.core.exceptions.auth import InvalidTelegramAuthPayload
from fanfan.presentation.web.telegram_oauth import (
    TELEGRAM_OAUTH_ERROR_CANCELLED,
    TELEGRAM_OAUTH_ERROR_FAILED,
    classify_oauth_error,
    read_telegram_claims,
)

pytestmark = pytest.mark.unit


def test_declining_on_telegram_is_reported_as_cancelled():
    error = OAuthError(error="access_denied", description="User denied the request")

    assert classify_oauth_error(error) == TELEGRAM_OAUTH_ERROR_CANCELLED


@pytest.mark.parametrize("error_code", ["mismatching_state", "invalid_grant", None])
def test_every_other_failure_collapses_to_failed(error_code: str | None):
    assert classify_oauth_error(OAuthError(error=error_code)) == (
        TELEGRAM_OAUTH_ERROR_FAILED
    )


def test_claims_are_read_from_the_parsed_id_token():
    token = {
        "access_token": "...",
        "userinfo": {"sub": "1234123412341234123", "id": 987654321, "name": "John Doe"},
    }

    claims = read_telegram_claims(token)

    assert claims.id == 987654321
    assert claims.name == "John Doe"


def test_token_without_an_id_token_is_rejected():
    with pytest.raises(InvalidTelegramAuthPayload):
        read_telegram_claims({"access_token": "..."})


# A bot signing with EdDSA or ES256K gets the `profile` scope rejected by
# Telegram, so the ID token verifies but carries no user to act on.
def test_token_without_profile_claims_is_rejected():
    token = {"userinfo": {"sub": "1234123412341234123"}}

    with pytest.raises(InvalidTelegramAuthPayload):
        read_telegram_claims(token)
