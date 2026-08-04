"""Shared pieces of the browser-facing OAuth flows (login and account linking).

The callback is entered by a top-level browser navigation coming back from the
provider, never by a fetch from the SPA. That makes an error *body* useless: the
browser would render the JSON as the page. So every failure here has to leave as
a redirect carrying a one-time code the frontend turns into a toast.

**One callback, two intents, one provider each.** Login and linking share a
single callback and are told apart by an `intent` stored in Authlib's state
payload — server-side, bound to the signed session cookie, single-use. The
provider, by contrast, stays in the URL path: RFC 9700 §4.4.2.2 requires a client
defending against mix-up attacks by redirect URI to "use a distinct redirection
URI for each issuer". That is the fallback defence here because Telegram does not
advertise `authorization_response_iss_parameter_supported`, so RFC 9207's `iss`
response parameter — which §4.4.2.1 prefers — is unavailable. Do not collapse the
provider into the state to save a route.
"""

import logging
from collections.abc import Mapping
from enum import StrEnum
from typing import Any
from urllib.parse import urlencode

import httpx
from authlib.integrations.starlette_client import OAuthError, StarletteOAuth2App
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from fanfan.core.exceptions.auth import InvalidTelegramAuthPayload
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)

# How long one authorization round-trip may take. Mirrors Authlib's own state
# TTL (`FrameworkIntegration.expires_in`), which the session cookie's max_age is
# set to match — see the SessionMiddleware comment in factory.py.
OAUTH_STATE_TTL_SECONDS = 3600

# The user declined on the provider's consent screen. Expected, not a fault.
OAUTH_ERROR_CANCELLED = "cancelled"
# Everything else: expired or replayed state, a failed token exchange, a token we
# cannot read. All of them look the same to the user, so they share one message.
OAUTH_ERROR_FAILED = "failed"

# Authlib passes the provider's `error` parameter through verbatim, and
# `access_denied` is the OAuth 2.0 code for a user who refused (RFC 6749 4.1.2.1).
_ACCESS_DENIED = "access_denied"

# Stable issuer identifiers per provider. Telegram publishes its issuer via OIDC
# discovery; VK ID does not expose a discovery endpoint, so the value is
# hardcoded. Both are compared in `read_flow_state` as a mix-up defence.
PROVIDER_ISSUERS: dict[SocialProvider, str] = {
    SocialProvider.TELEGRAM: "https://oauth.telegram.org",
    SocialProvider.VK: "https://id.vk.ru",
}


class OAuthIntent(StrEnum):
    """Why a flow was started. Decided at the start route, never at the callback.

    Never inferred from whether a session cookie happens to be present: a signed-in
    user clicking "log in with Telegram" would silently link instead, and a
    signed-out user finishing a link would be logged in as the account's owner.
    """

    LOGIN = "login"
    LINK = "link"


class OAuthFlowState(BaseModel):
    """The part of Authlib's state payload this app puts there itself.

    Lives in the state store, not in the `state` parameter, so it cannot be
    tampered with in transit — which is how RFC 9700 §4.7.1's "clients MUST
    protect `state` against tampering" is satisfied here without signing anything.
    """

    intent: OAuthIntent
    # RFC 9700 §4.4.2: "clients MUST store, for each authorization request, the
    # issuer they sent the authorization request to and bind this information to
    # the user agent." Authlib binds it — it refuses a state with no matching
    # marker in the signed session cookie — and the callback compares it back.
    issuer: str
    # Only set for LINK: who asked for it. Compared against the session at the
    # callback so a mid-flow login as somebody else cannot retarget the link.
    initiator_user_id: UserId | None = None


class TelegramClaims(BaseModel):
    """The subset of Telegram's ID token the app acts on.

    `sub` is the identity key and `id` is only ever an address — see the
    `SocialIdentity` docstring for why they are stored separately.

    `name` and `id` are `profile`-scope claims. Telegram rejects that scope
    outright when the bot is switched to EdDSA or ES256K signing in BotFather, so
    a bot misconfigured there arrives with a valid, signature-checked token that
    carries neither. `sub` survives that (it needs only `openid`), which is why it
    is the one field with no fallback — and why the other two are optional here
    rather than indexed directly.
    """

    sub: str
    id: int | None = None
    name: str | None = None


class VkClaims(BaseModel):
    """Claims extracted from VK ID's ``/oauth2/user_info`` response.

    ``user_id`` is the stable numeric VK user identifier; it is stored as
    ``str(user_id)`` in the ``subject`` column of ``SocialIdentity``.
    """

    user_id: int
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


def classify_oauth_error(error: OAuthError) -> str:
    """Map an Authlib failure onto the code the frontend has copy for."""
    if error.error == _ACCESS_DENIED:
        return OAUTH_ERROR_CANCELLED

    return OAUTH_ERROR_FAILED


class OAuthFailed(Exception):
    """A callback that cannot continue, carrying a code the frontend has copy for.

    Exists so the callback translates *every* failure into a redirect. See the
    module docstring for why an error body is useless on this route.
    """

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


async def start_oauth_flow(
    client: StarletteOAuth2App,
    request: Request,
    redirect_uri: str,
    flow_state: OAuthFlowState,
) -> str:
    """Build the authorization URL and stash `flow_state` with Authlib's state.

    Deliberately not `authorize_redirect`: that forwards its extra kwargs into
    `create_authorization_url`, which would send them to the provider as query
    parameters. `save_authorize_data` stores everything except `state` in the
    state payload instead, and `_format_state_params` reads only `code_verifier`
    and `redirect_uri` back out, so these extra keys ride along untouched.
    """
    rv = await client.create_authorization_url(redirect_uri)
    await client.save_authorize_data(
        request,
        redirect_uri=redirect_uri,
        **flow_state.model_dump(mode="json"),
        **rv,
    )
    return rv["url"]


async def read_flow_state(
    client: StarletteOAuth2App,
    request: Request,
    provider: SocialProvider,
) -> OAuthFlowState:
    """Recover the flow state, or raise OAuthFailed if it cannot be trusted.

    Must run *before* the token exchange: `authorize_access_token` clears the
    state payload and does not hand it back, so there is no reading it afterwards.
    `get_state_data` is non-destructive, which is why calling it first is safe.
    """
    state = request.query_params.get("state")
    if not state:
        logger.info("OAuth callback carried no state")
        raise OAuthFailed(OAUTH_ERROR_FAILED)

    # Reaching past the app to its framework integration is the only way to read
    # the payload we stored; `authorize_access_token` consumes it silently.
    state_data = await client.framework.get_state_data(request.session, state)
    if not state_data:
        # Expired, replayed, or started in a different browser. Authlib would
        # raise the same way a moment later; failing here keeps the error one
        # kind rather than two.
        logger.info("OAuth callback state is missing or already used")
        raise OAuthFailed(OAUTH_ERROR_FAILED)

    try:
        flow_state = OAuthFlowState.model_validate(state_data)
    except ValidationError as e:
        logger.warning("OAuth state payload could not be read")
        raise OAuthFailed(OAUTH_ERROR_FAILED) from e

    # RFC 9700 §4.4.2.1: a response whose issuer is not the one the request
    # went to must abort the interaction.  Telegram publishes its issuer via
    # OIDC discovery; VK does not, so PROVIDER_ISSUERS carries a static value.
    expected_issuer = PROVIDER_ISSUERS.get(provider)
    if flow_state.issuer != expected_issuer:
        logger.warning(
            "OAuth callback issuer does not match the authorization request",
            extra={"expected_issuer": expected_issuer},
        )
        raise OAuthFailed(OAUTH_ERROR_FAILED)

    return flow_state


async def fetch_telegram_claims(
    telegram: StarletteOAuth2App, request: Request
) -> TelegramClaims:
    """Finish the OAuth round-trip, or raise OAuthFailed with a code.

    Authlib raises three unrelated exception families out of this one call and
    only one of them descends from OAuthError: httpx errors escape the token
    exchange (`parse_response_token` re-raises a 5xx) and the JWKS fetch, jose
    errors escape ID token validation, and a token endpoint answering
    `{"error": ...}` raises OAuth2Error — a sibling of OAuthError, not a
    subclass. Narrow `except` clauses let all of those reach the JSON exception
    handlers, which on a browser navigation means the user reads
    `{"code": "INTERNAL_ERROR"}` as the page.
    """
    try:
        token = await telegram.authorize_access_token(request)
        return read_telegram_claims(token)
    except OAuthError as e:
        # Declining on Telegram, letting the state expire (Authlib gives it an
        # hour) and re-opening an already-used callback URL all land here. None
        # of them is a server fault, so this stays below warning level.
        logger.info(
            "Telegram authorization did not complete", extra={"oauth_error": e.error}
        )
        raise OAuthFailed(classify_oauth_error(e)) from e
    except InvalidTelegramAuthPayload as e:
        # Signature-valid token, unusable content — almost always the bot's
        # signing algorithm in BotFather stripping the `profile` scope.
        logger.warning("Telegram ID token carried no usable profile claims")
        raise OAuthFailed(OAUTH_ERROR_FAILED) from e
    except Exception as e:
        # Deliberately broad — narrowing this back to an exception list is what
        # the docstring above argues against, and the cost is a JSON page.
        logger.exception("Telegram token exchange failed")
        raise OAuthFailed(OAUTH_ERROR_FAILED) from e


def read_telegram_claims(token: Mapping[str, Any]) -> TelegramClaims:
    """Pull the claims we act on out of an Authlib-validated token.

    Authlib has already verified the signature, `iss`, `aud`, `exp` and `nonce`
    by the time a token reaches here — this only checks that the payload has the
    shape we need. `userinfo` is absent when the response carried no `id_token`.
    """
    userinfo = token.get("userinfo")
    if not isinstance(userinfo, Mapping):
        raise InvalidTelegramAuthPayload

    try:
        claims = TelegramClaims.model_validate(dict(userinfo))
    except ValidationError as e:
        raise InvalidTelegramAuthPayload from e

    if claims.id is None:
        # Not fatal — `sub` alone identifies the user, so the login proceeds and
        # only Telegram notifications are unavailable (the notifier treats a
        # missing address as UserNotReachable, and the next login carrying an id
        # backfills it). Logged loudly because the cause is almost always the
        # bot's signing algorithm in BotFather stripping the `profile` scope,
        # which is a misconfiguration nobody would otherwise notice.
        logger.warning(
            "Telegram ID token carried no `id` claim — "
            "notifications will not reach this user until it does"
        )

    return claims


_VK_USERINFO_URL = "https://id.vk.ru/oauth2/user_info"


async def fetch_vk_claims(vk: StarletteOAuth2App, request: Request) -> VkClaims:
    """Exchange the authorization code and fetch the VK ID user profile.

    VK ID deviates from standard OAuth in three ways handled here:

    1. The callback carries a ``device_id`` query parameter that must be
       forwarded to the token endpoint (Authlib passes extra kwargs through).
    2. The token endpoint requires ``state`` in the POST body. Authlib's
       ``fetch_token`` consumes ``state`` as a named parameter without
       forwarding it to ``_prepare_token_endpoint_body``, so we inject it
       via the ``body`` seed string that ``_prepare_token_endpoint_body``
       appends the other params to.
    3. The user-info endpoint is a POST that takes ``client_id`` and
       ``access_token`` in the form body, not a GET with a Bearer token.
    """
    try:
        device_id = request.query_params.get("device_id", "")
        state = request.query_params.get("state", "")
        token = await vk.authorize_access_token(
            request, device_id=device_id, body=urlencode({"state": state})
        )

        async with httpx.AsyncClient() as http:
            resp = await http.post(
                _VK_USERINFO_URL,
                data={
                    "client_id": vk.client_id,
                    "access_token": token["access_token"],
                },
            )
            resp.raise_for_status()

        user = resp.json().get("user")
        if not isinstance(user, dict):
            logger.warning("VK user_info response carried no user object")
            raise OAuthFailed(OAUTH_ERROR_FAILED)  # noqa: TRY301

        return VkClaims.model_validate(user)
    except OAuthError as e:
        logger.info("VK authorization did not complete", extra={"oauth_error": e.error})
        raise OAuthFailed(classify_oauth_error(e)) from e
    except OAuthFailed:
        raise
    except Exception as e:
        logger.exception("VK token exchange or user-info fetch failed")
        raise OAuthFailed(OAUTH_ERROR_FAILED) from e
