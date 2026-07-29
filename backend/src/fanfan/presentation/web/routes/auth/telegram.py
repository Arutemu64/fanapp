import logging
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from starlette import status
from starlette.responses import RedirectResponse, Response

from fanfan.application.interactors.auth.authorize_telegram import (
    AuthorizeTelegram,
    AuthorizeTelegramInput,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.telegram_oauth import (
    TELEGRAM_OAUTH_ERROR_FAILED,
    TelegramOAuthFailed,
    fetch_telegram_claims,
)

logger = logging.getLogger(__name__)

telegram_router = APIRouter()

# Frontend reads this one-time code from the login URL and shows a safe toast.
TELEGRAM_LOGIN_ERROR_QUERY_PARAM = "telegramLoginError"


def _build_login_redirect(error_code: str) -> RedirectResponse:
    query = urlencode({TELEGRAM_LOGIN_ERROR_QUERY_PARAM: error_code})

    return RedirectResponse(f"/login?{query}", status_code=status.HTTP_303_SEE_OTHER)


@telegram_router.get(
    "/login/telegram",
    summary="Start Telegram login",
    description="Redirects the browser to Telegram's OAuth authorization page. "
    "Telegram then calls back to the authorize endpoint to finish the login. "
    "If the redirect cannot be built the browser goes back to the login page "
    "with a `telegramLoginError` query param instead.",
    responses={
        302: {"description": "Redirect to Telegram's OAuth authorization page."},
        303: {
            "description": "Telegram could not be reached. Redirects to the login "
            "page with a `telegramLoginError` query param."
        },
    },
)
@inject
async def login_telegram(
    request: Request,
    oauth: FromDishka[OAuth],
) -> Response:
    telegram: StarletteOAuth2App = oauth.create_client("telegram")
    redirect_uri = request.url_for("authorize_telegram")

    try:
        return await telegram.authorize_redirect(request, redirect_uri)
    except Exception:
        # Building the redirect needs Telegram's discovery document. The registry
        # is APP-scoped so it is fetched once per process — this is the first
        # login after a restart running into an unreachable Telegram, or a
        # discovery document we cannot parse.
        logger.exception("Could not reach Telegram to start the login")
        return _build_login_redirect(TELEGRAM_OAUTH_ERROR_FAILED)


# URL path pattern (.../telegram, .../telegram/callback) mirrors the
# account-linking pair in current_user/connections.py, so the two OAuth
# flows read alike.
@telegram_router.get(
    "/login/telegram/callback",
    summary="Finish Telegram login",
    description="OAuth callback for Telegram login. Authenticates the user from the "
    "Telegram payload, sets the session cookie and redirects to the app root. "
    "Every failure — cancelled on Telegram, an unusable token, an unreachable "
    "Telegram or database — redirects to the login page with a "
    "`telegramLoginError` query param the frontend turns into a toast; this route "
    "never answers with an error body, because the browser would render it as the "
    "page. Invoked by Telegram, not called directly by the frontend.",
    responses={
        303: {
            "description": "Login finished. On success the session cookie is set and "
            "the browser goes to the app root; otherwise it goes to the login page "
            "with a `telegramLoginError` query param."
        },
    },
)
@inject
async def authorize_telegram(
    request: Request,
    config: FromDishka[WebConfig],
    oauth: FromDishka[OAuth],
    interactor: FromDishka[AuthorizeTelegram],
) -> RedirectResponse:
    telegram: StarletteOAuth2App = oauth.create_client("telegram")

    try:
        claims = await fetch_telegram_claims(telegram, request)
    except TelegramOAuthFailed as e:
        return _build_login_redirect(e.error_code)

    try:
        session_id = await interactor(
            AuthorizeTelegramInput(user_id=claims.id, name=claims.name)
        )
    except Exception:
        # The account is created and the session issued here, so an unreachable
        # database or session store fails a login Telegram already approved. The
        # browser is mid-navigation either way, so this has to leave as a
        # redirect rather than a JSON body.
        logger.exception("Could not create a session for a Telegram login")
        return _build_login_redirect(TELEGRAM_OAUTH_ERROR_FAILED)

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(response, session_id, config)
    return response
