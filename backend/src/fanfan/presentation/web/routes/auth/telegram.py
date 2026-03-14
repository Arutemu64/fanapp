from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from starlette import status
from starlette.responses import RedirectResponse

from fanfan.application.auth.authorize_telegram import (
    AuthorizeTelegram,
    AuthorizeTelegramCommand,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookies

telegram_router = APIRouter()


@telegram_router.get("/login/telegram")
@inject
async def login_telegram(
    request: Request,
    oauth: FromDishka[OAuth],
) -> None:
    telegram: StarletteOAuth2App = oauth.create_client("telegram")
    redirect_uri = request.url_for("authorize_telegram")
    return await telegram.authorize_redirect(request, redirect_uri)


@telegram_router.get("/auth/telegram")
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
    token = await interactor(
        AuthorizeTelegramCommand(user_id=userinfo["id"], name=userinfo["name"])
    )
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookies(response, token.access_token, token.refresh_token, config)
    return response
