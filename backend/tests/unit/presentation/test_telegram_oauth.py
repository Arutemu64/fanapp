from collections.abc import Mapping
from typing import Any, cast

import httpx
import pytest
from authlib.integrations.starlette_client import OAuthError
from authlib.oauth2.base import OAuth2Error
from joserfc.errors import BadSignatureError, ExpiredTokenError, InvalidClaimError

from fanfan.core.exceptions.auth import InvalidTelegramAuthPayload
from fanfan.presentation.web.telegram_oauth import (
    TELEGRAM_OAUTH_ERROR_CANCELLED,
    TELEGRAM_OAUTH_ERROR_FAILED,
    TelegramOAuthFailed,
    classify_oauth_error,
    fetch_telegram_claims,
    read_telegram_claims,
)

pytestmark = pytest.mark.unit

VALID_TOKEN = {
    "access_token": "...",
    "userinfo": {"sub": "1234123412341234123", "id": 987654321, "name": "John Doe"},
}


class FakeTelegramApp:
    """Stands in for Authlib's StarletteOAuth2App in the token-exchange step.

    `authorize_access_token` is the single call that reaches Telegram, so raising
    from it reproduces every callback failure without a network or a real token.
    """

    def __init__(
        self,
        *,
        raises: Exception | None = None,
        token: Mapping[str, Any] = VALID_TOKEN,
    ) -> None:
        self._raises = raises
        self._token = token

    async def authorize_access_token(self, request: Any) -> Mapping[str, Any]:  # noqa: ARG002
        if self._raises is not None:
            raise self._raises

        return self._token


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


async def _fetch_claims(app: FakeTelegramApp):
    # fetch_telegram_claims only forwards the request to Authlib, so a sentinel
    # stands in for the real one.
    return await fetch_telegram_claims(cast("Any", app), cast("Any", object()))


async def test_a_completed_exchange_returns_the_claims():
    claims = await _fetch_claims(FakeTelegramApp())

    assert claims.id == 987654321
    assert claims.name == "John Doe"


async def test_declining_on_telegram_survives_as_cancelled():
    app = FakeTelegramApp(raises=OAuthError(error="access_denied"))

    with pytest.raises(TelegramOAuthFailed) as failure:
        await _fetch_claims(app)

    assert failure.value.error_code == TELEGRAM_OAUTH_ERROR_CANCELLED


# Every one of these escapes an `except OAuthError` clause: httpx errors come out
# of the token exchange and the JWKS fetch, joserfc errors out of ID token
# validation, and OAuth2Error is a sibling of OAuthError rather than a subclass.
# Uncaught, they reach the JSON exception handlers and the user — mid-navigation
# — reads `{"code": "INTERNAL_ERROR"}` as the page.
@pytest.mark.parametrize(
    "error",
    [
        pytest.param(httpx.ConnectError("dns failure"), id="telegram_unreachable"),
        pytest.param(
            httpx.HTTPStatusError(
                "server error",
                request=httpx.Request("POST", "https://oauth.telegram.org/token"),
                response=httpx.Response(500),
            ),
            id="token_endpoint_5xx",
        ),
        pytest.param(
            OAuth2Error(error="invalid_grant", description="Bad authorization code"),
            id="authorization_code_rejected",
        ),
        pytest.param(BadSignatureError(), id="id_token_signature_invalid"),
        pytest.param(InvalidClaimError("nonce"), id="id_token_nonce_mismatch"),
        pytest.param(ExpiredTokenError("exp"), id="id_token_expired"),
        pytest.param(
            RuntimeError('Missing "jwks_uri" in metadata'), id="discovery_incomplete"
        ),
    ],
)
async def test_non_oauth_failures_still_get_an_error_code(error: Exception):
    with pytest.raises(TelegramOAuthFailed) as failure:
        await _fetch_claims(FakeTelegramApp(raises=error))

    assert failure.value.error_code == TELEGRAM_OAUTH_ERROR_FAILED


async def test_a_token_without_profile_claims_gets_an_error_code():
    app = FakeTelegramApp(token={"userinfo": {"sub": "1234123412341234123"}})

    with pytest.raises(TelegramOAuthFailed) as failure:
        await _fetch_claims(app)

    assert failure.value.error_code == TELEGRAM_OAUTH_ERROR_FAILED
