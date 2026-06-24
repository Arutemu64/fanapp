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

telegram_router = APIRouter()


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
    return await telegram.authorize_redirect(request, redirect_uri)


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
    telegram: StarletteOAuth2App = oauth.create_client("telegram")
    token = await telegram.authorize_access_token(request)
    userinfo = token.get("userinfo", {})
    session_id = await interactor(
        AuthorizeTelegramInput(user_id=userinfo["id"], name=userinfo["name"])
    )
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(response, session_id, config)
    return response
