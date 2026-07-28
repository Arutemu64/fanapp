"""Shared pieces of the two browser-facing Telegram OAuth callbacks.

Both callbacks are entered by a top-level browser navigation coming back from
Telegram, never by a fetch from the SPA. That makes an error *body* useless: the
browser would render the JSON as the page. So every failure here has to leave as
a redirect carrying a one-time code the frontend turns into a toast.
"""

from collections.abc import Mapping
from typing import Any

from authlib.integrations.starlette_client import OAuthError
from pydantic import BaseModel, ValidationError

from fanfan.core.exceptions.auth import InvalidTelegramAuthPayload

# How long one authorization round-trip may take. Mirrors Authlib's own state
# TTL (`FrameworkIntegration.expires_in`), which the session cookie's max_age is
# set to match — see the SessionMiddleware comment in factory.py.
OAUTH_STATE_TTL_SECONDS = 3600

# The user declined on Telegram's consent screen. Expected, not a fault.
TELEGRAM_OAUTH_ERROR_CANCELLED = "cancelled"
# Everything else: expired or replayed state, a failed token exchange, a token we
# cannot read. All of them look the same to the user, so they share one message.
TELEGRAM_OAUTH_ERROR_FAILED = "failed"

# Authlib passes the provider's `error` parameter through verbatim, and
# `access_denied` is the OAuth 2.0 code for a user who refused (RFC 6749 4.1.2.1).
_ACCESS_DENIED = "access_denied"


class TelegramClaims(BaseModel):
    """The subset of Telegram's ID token the app acts on.

    Both fields are `profile`-scope claims. Telegram rejects that scope outright
    when the bot is switched to EdDSA or ES256K signing in BotFather, so a bot
    misconfigured there arrives with a valid, signature-checked token that
    carries no user at all — hence the guard rather than direct indexing.
    `id` is not even in the discovery document's `claims_supported`, though
    Telegram's docs and sample token both include it, so treat it as advertised
    by the prose only.

    Identity is keyed on `id` rather than the OIDC `sub` on purpose. They are
    different values (Telegram's own example pairs `id: 987654321` with
    `sub: "1234123412341234123"`), and only `id` is the Bot API user id the
    notifier needs to message the user afterwards. `sub` would otherwise be the
    orthodox choice: the discovery document declares `subject_types_supported:
    ["public"]`, so it is stable and identical across clients.
    """

    id: int
    name: str


def classify_oauth_error(error: OAuthError) -> str:
    """Map an Authlib failure onto the code the frontend has copy for."""
    if error.error == _ACCESS_DENIED:
        return TELEGRAM_OAUTH_ERROR_CANCELLED

    return TELEGRAM_OAUTH_ERROR_FAILED


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
        return TelegramClaims.model_validate(dict(userinfo))
    except ValidationError as e:
        raise InvalidTelegramAuthPayload from e
