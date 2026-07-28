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
from fanfan.presentation.web.csrf import ensure_trusted_origin
from fanfan.presentation.web.oauth import (
    TELEGRAM_CLIENT_NAME,
    start_telegram_authorization,
)
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ErrorMessage

telegram_router = APIRouter()


@telegram_router.post(
    "/login/telegram",
    summary="Start Telegram login",
    description="Redirects the browser to Telegram's OAuth authorization page. "
    "Telegram then calls back to the authorize endpoint to finish the login.\n\n"
    "Submit this as a same-origin form, not a link: a GET flow-start can be "
    "triggered cross-site by any page, so the request initiator is verified.",
    responses={
        303: {"description": "Redirect to Telegram's OAuth authorization page."},
        403: {
            "model": ErrorMessage,
            "description": "Request did not originate from a trusted origin.",
        },
    },
)
@inject
async def login_telegram(
    request: Request,
    config: FromDishka[WebConfig],
    oauth: FromDishka[OAuth],
) -> Response:
    ensure_trusted_origin(request, config)
    redirect_uri = request.url_for("authorize_telegram")
    return await start_telegram_authorization(request, oauth, redirect_uri)


@telegram_router.get(
    "/auth/telegram",
    summary="Finish Telegram login",
    description="OAuth callback for Telegram login. Authenticates the user from the "
    "Telegram payload, sets the session cookie and redirects to the app root. "
    "Invoked by Telegram, not called directly by the frontend.",
    responses={
        303: {"description": "Login successful. Session cookie set, redirect to app."},
    },
)
@inject
async def authorize_telegram(
    request: Request,
    config: FromDishka[WebConfig],
    oauth: FromDishka[OAuth],
    interactor: FromDishka[AuthorizeTelegram],
) -> RedirectResponse:
    telegram: StarletteOAuth2App = oauth.create_client(TELEGRAM_CLIENT_NAME)
    token = await telegram.authorize_access_token(request)
    userinfo = token.get("userinfo", {})
    session_id = await interactor(
        AuthorizeTelegramInput(user_id=userinfo["id"], name=userinfo["name"])
    )
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(response, session_id, config)
    return response
