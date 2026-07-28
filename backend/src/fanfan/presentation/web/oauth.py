from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from fastapi import Request
from starlette import status
from starlette.responses import RedirectResponse

TELEGRAM_CLIENT_NAME = "telegram"


async def start_telegram_authorization(
    request: Request,
    oauth: OAuth,
    redirect_uri: str,
) -> RedirectResponse:
    """Begin a Telegram OAuth handshake and redirect the browser to Telegram.

    Inlines what authlib's `authorize_redirect` does, for the status code alone:
    it hardcodes 302, and a 302 answering a POST leaves it to the browser whether
    to replay the POST against Telegram's authorization endpoint, which only
    accepts GET. 303 states that explicitly. The flow-start endpoints are POST
    because a GET one is CSRF-triggerable (see `csrf.ensure_trusted_origin`).
    """
    telegram: StarletteOAuth2App = oauth.create_client(TELEGRAM_CLIENT_NAME)
    # Carries `url` plus the values authlib binds to the session — `state`, and
    # `nonce`/`code_verifier` for OIDC + PKCE — which save_authorize_data stores.
    authorization = await telegram.create_authorization_url(redirect_uri)
    await telegram.save_authorize_data(
        request, redirect_uri=redirect_uri, **authorization
    )
    return RedirectResponse(authorization["url"], status_code=status.HTTP_303_SEE_OTHER)
