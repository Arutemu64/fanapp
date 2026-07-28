import logging
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, OAuthError, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from httpx import HTTPError
from starlette import status
from starlette.responses import RedirectResponse, Response

from fanfan.application.interactors.auth.authorize_telegram import (
    AuthorizeTelegram,
    AuthorizeTelegramInput,
)
from fanfan.core.exceptions.auth import InvalidTelegramAuthPayload
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.telegram_oauth import (
    TELEGRAM_OAUTH_ERROR_FAILED,
    classify_oauth_error,
    read_telegram_claims,
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
    "Telegram then calls back to the authorize endpoint to finish the login.",
    responses={
        302: {"description": "Redirect to Telegram's OAuth authorization page."},
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
    except HTTPError:
        # Building the redirect needs Telegram's discovery document. The registry
        # is APP-scoped so it is fetched once per process — this is the first
        # login after a restart running into an unreachable Telegram.
        logger.warning("Could not reach Telegram to start the login")
        return _build_login_redirect(TELEGRAM_OAUTH_ERROR_FAILED)


# Start/callback pair named the same way as the account-linking one in
# current_user/connections.py, so the two OAuth flows read alike.
@telegram_router.get(
    "/login/telegram/callback",
    summary="Finish Telegram login",
    description="OAuth callback for Telegram login. Authenticates the user from the "
    "Telegram payload, sets the session cookie and redirects to the app root. "
    "A failed or cancelled login redirects to the login page with a "
    "`telegramLoginError` query param the frontend turns into a toast. "
    "Invoked by Telegram, not called directly by the frontend.",
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
        token = await telegram.authorize_access_token(request)
        claims = read_telegram_claims(token)
    except OAuthError as e:
        # Declining on Telegram, letting the state expire (Authlib gives it an
        # hour) and re-opening an already-used callback URL all land here. None
        # of them is a server fault, so this stays below warning level.
        logger.info("Telegram login did not complete", extra={"oauth_error": e.error})
        return _build_login_redirect(classify_oauth_error(e))
    except InvalidTelegramAuthPayload:
        # Signature-valid token, unusable content — almost always the bot's
        # signing algorithm in BotFather stripping the `profile` scope.
        logger.warning("Telegram ID token carried no usable profile claims")
        return _build_login_redirect(TELEGRAM_OAUTH_ERROR_FAILED)

    session_id = await interactor(
        AuthorizeTelegramInput(user_id=claims.id, name=claims.name)
    )
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(response, session_id, config)
    return response
