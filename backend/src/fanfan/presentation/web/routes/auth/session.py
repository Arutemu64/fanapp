from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request, Response
from starlette import status

from fanfan.application.interactors.auth.logout_user import LogoutUser
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import (
    SESSION_COOKIE_NAME,
    delete_auth_cookie,
)

session_router = APIRouter()


@session_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="Clears session cookie and removes Redis session state.",
    responses={204: {"description": "Successfully logged out."}},
)
@inject
async def logout_user(
    request: Request,
    response: Response,
    interactor: FromDishka[LogoutUser],
    config: FromDishka[WebConfig],
) -> None:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    await interactor(session_id)

    # config is intentionally kept in the signature for DI consistency.
    _ = config
    delete_auth_cookie(response)
