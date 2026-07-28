from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from fastapi import Request
from starlette import status
from starlette.datastructures import URL
from starlette.responses import RedirectResponse

TELEGRAM_CLIENT_NAME = "telegram"


async def start_telegram_authorization(
    request: Request,
    oauth: OAuth,
    redirect_uri: URL,
) -> RedirectResponse:
    """Begin a Telegram OAuth handshake and redirect the browser to Telegram."""
    telegram: StarletteOAuth2App = oauth.create_client(TELEGRAM_CLIENT_NAME)
    response = await telegram.authorize_redirect(request, redirect_uri)
    # authlib hardcodes 302, and RFC 9110 only says a user agent *may* rewrite a
    # redirected POST to GET — every browser does, but Telegram's authorization
    # endpoint accepts GET only, so nothing here should hinge on that. 303 states
    # it outright. The flow-start endpoints are POST because a GET one is
    # CSRF-triggerable (see `csrf.ensure_trusted_origin`).
    response.status_code = status.HTTP_303_SEE_OTHER
    return response
