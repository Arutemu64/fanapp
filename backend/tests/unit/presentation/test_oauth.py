from collections.abc import Mapping
from typing import Any, cast

import httpx
import pytest
from authlib.integrations.starlette_client import OAuthError
from authlib.oauth2.base import OAuth2Error
from joserfc.errors import BadSignatureError, ExpiredTokenError, InvalidClaimError

from fanfan.core.exceptions.auth import InvalidTelegramAuthPayload
from fanfan.presentation.web.oauth import (
    OAUTH_ERROR_CANCELLED,
    OAUTH_ERROR_FAILED,
    OAuthFailed,
    OAuthFlowState,
    OAuthIntent,
    classify_oauth_error,
    fetch_telegram_claims,
    read_flow_state,
    read_telegram_claims,
)

pytestmark = pytest.mark.unit

ISSUER = "https://oauth.telegram.org"
# Telegram's own sample token pairs these — deliberately different values, so a
# test that confused the two would fail rather than pass by coincidence.
SUBJECT = "1234123412341234123"
TELEGRAM_USER_ID = 987654321

VALID_TOKEN = {
    "access_token": "...",
    "userinfo": {"sub": SUBJECT, "id": TELEGRAM_USER_ID, "name": "John Doe"},
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
        state_data: Mapping[str, Any] | None = None,
        issuer: str = ISSUER,
    ) -> None:
        self._raises = raises
        self._token = token
        self.framework = FakeFramework(state_data)
        self._issuer = issuer

    async def authorize_access_token(self, request: Any) -> Mapping[str, Any]:  # noqa: ARG002
        if self._raises is not None:
            raise self._raises

        return self._token

    async def load_server_metadata(self) -> Mapping[str, Any]:
        return {"issuer": self._issuer}


class FakeFramework:
    def __init__(self, state_data: Mapping[str, Any] | None) -> None:
        self._state_data = state_data

    async def get_state_data(
        self,
        session: Any,  # noqa: ARG002
        state: str,  # noqa: ARG002
    ) -> Mapping[str, Any] | None:
        return self._state_data


class FakeRequest:
    def __init__(self, state: str | None) -> None:
        self.query_params = {"state": state} if state is not None else {}
        self.session: dict[str, Any] = {}


def _login_state(**overrides: Any) -> dict[str, Any]:
    return {"intent": "login", "issuer": ISSUER} | overrides


def test_declining_on_telegram_is_reported_as_cancelled():
    error = OAuthError(error="access_denied", description="User denied the request")

    assert classify_oauth_error(error) == OAUTH_ERROR_CANCELLED


@pytest.mark.parametrize("error_code", ["mismatching_state", "invalid_grant", None])
def test_every_other_failure_collapses_to_failed(error_code: str | None):
    assert classify_oauth_error(OAuthError(error=error_code)) == OAUTH_ERROR_FAILED


def test_claims_are_read_from_the_parsed_id_token():
    claims = read_telegram_claims(VALID_TOKEN)

    # The subject is the identity; the Bot API id is only a delivery address.
    assert claims.sub == SUBJECT
    assert claims.id == TELEGRAM_USER_ID
    assert claims.name == "John Doe"


def test_token_without_an_id_token_is_rejected():
    with pytest.raises(InvalidTelegramAuthPayload):
        read_telegram_claims({"access_token": "..."})


def test_token_without_a_subject_is_rejected():
    with pytest.raises(InvalidTelegramAuthPayload):
        read_telegram_claims({"userinfo": {"id": TELEGRAM_USER_ID}})


# A bot signing with EdDSA or ES256K gets the `profile` scope rejected by
# Telegram, so the ID token verifies but carries no `id`. That is a degraded
# login (no notification address), not a failed one — `sub` still identifies,
# and the next login carrying an id backfills it.
def test_token_without_profile_claims_still_identifies_the_user():
    claims = read_telegram_claims({"userinfo": {"sub": SUBJECT}})

    assert claims.sub == SUBJECT
    assert claims.id is None


async def _fetch_claims(app: FakeTelegramApp):
    # fetch_telegram_claims only forwards the request to Authlib, so a sentinel
    # stands in for the real one.
    return await fetch_telegram_claims(cast("Any", app), cast("Any", object()))


async def test_a_completed_exchange_returns_the_claims():
    claims = await _fetch_claims(FakeTelegramApp())

    assert claims.sub == SUBJECT
    assert claims.id == TELEGRAM_USER_ID


async def test_declining_on_telegram_survives_as_cancelled():
    app = FakeTelegramApp(raises=OAuthError(error="access_denied"))

    with pytest.raises(OAuthFailed) as failure:
        await _fetch_claims(app)

    assert failure.value.error_code == OAUTH_ERROR_CANCELLED


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
    with pytest.raises(OAuthFailed) as failure:
        await _fetch_claims(FakeTelegramApp(raises=error))

    assert failure.value.error_code == OAUTH_ERROR_FAILED


async def test_a_token_without_a_subject_gets_an_error_code():
    app = FakeTelegramApp(token={"userinfo": {"id": TELEGRAM_USER_ID}})

    with pytest.raises(OAuthFailed) as failure:
        await _fetch_claims(app)

    assert failure.value.error_code == OAUTH_ERROR_FAILED


async def _read_state(app: FakeTelegramApp, state: str | None) -> OAuthFlowState:
    return await read_flow_state(cast("Any", app), cast("Any", FakeRequest(state)))


async def test_flow_state_round_trips_the_intent():
    app = FakeTelegramApp(state_data=_login_state())

    flow_state = await _read_state(app, "abc")

    assert flow_state.intent is OAuthIntent.LOGIN


async def test_link_state_carries_the_initiator():
    initiator = "0199a1f0-0000-7000-8000-000000000000"
    app = FakeTelegramApp(
        state_data=_login_state(intent="link", initiator_user_id=initiator)
    )

    flow_state = await _read_state(app, "abc")

    assert flow_state.intent is OAuthIntent.LINK
    assert str(flow_state.initiator_user_id) == initiator


# The intent decides whether the callback issues a session or attaches an
# identity, so a callback that cannot produce a trustworthy one must run neither
# branch.
@pytest.mark.parametrize(
    ("state", "state_data"),
    [
        pytest.param(None, _login_state(), id="no_state_parameter"),
        pytest.param("abc", None, id="state_expired_or_replayed"),
        pytest.param("abc", {"issuer": ISSUER}, id="intent_missing"),
        pytest.param(
            "abc", _login_state(intent="delete_everything"), id="bogus_intent"
        ),
    ],
)
async def test_untrustworthy_state_is_refused(
    state: str | None, state_data: Mapping[str, Any] | None
):
    app = FakeTelegramApp(state_data=state_data)

    with pytest.raises(OAuthFailed) as failure:
        await _read_state(app, state)

    assert failure.value.error_code == OAUTH_ERROR_FAILED


# RFC 9700 §4.4.2.1: a response whose issuer is not the one the request went to
# must abort the interaction. Telegram does not support the RFC 9207 `iss`
# response parameter, so this comparison against the stored issuer, plus the
# per-provider callback URI, is the whole mix-up defence.
async def test_an_issuer_that_moved_mid_flow_is_refused():
    app = FakeTelegramApp(
        state_data=_login_state(issuer="https://evil.example"), issuer=ISSUER
    )

    with pytest.raises(OAuthFailed) as failure:
        await _read_state(app, "abc")

    assert failure.value.error_code == OAUTH_ERROR_FAILED
