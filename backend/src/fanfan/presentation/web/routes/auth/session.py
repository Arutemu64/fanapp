from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request, Response
from starlette import status

from fanfan.application.interactors.auth.logout_user import LogoutUser
from fanfan.presentation.web.routes.auth.cookies import (
    SESSION_COOKIE_NAME,
    delete_auth_cookie,
)

session_router = APIRouter()


@session_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description=(
        "Clears session cookie and removes Redis session state; also emits "
        "Clear-Site-Data so the browser drops cookies itself."
    ),
    responses={204: {"description": "Successfully logged out."}},
)
@inject
async def logout_user(
    request: Request,
    response: Response,
    interactor: FromDishka[LogoutUser],
) -> None:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    await interactor(session_id)
    delete_auth_cookie(response)
    # Belt-and-suspenders on top of the Set-Cookie deletion above: ask the browser
    # to drop cookies itself so a session cookie can't survive a failed clear. Scoped
    # to "cookies" only — "storage"/"cache" would wipe the offline IndexedDB caches
    # (the public schedule we keep for guests) and unregister the service worker.
    # HTTPS-only; ignored on plain HTTP. https://developer.mozilla.org/docs/Web/HTTP/Reference/Headers/Clear-Site-Data
    response.headers["Clear-Site-Data"] = '"cookies"'
