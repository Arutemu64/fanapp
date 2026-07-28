from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from starlette import status
from starlette.responses import RedirectResponse, Response

from fanfan.application.interactors.current_user.link_telegram_account import (
    LinkTelegramAccount,
    LinkTelegramAccountInput,
)
from fanfan.application.interactors.current_user.unlink_telegram_account import (
    UnlinkTelegramAccount,
)
from fanfan.core.exceptions.auth import InvalidTelegramAuthPayload
from fanfan.core.exceptions.users import (
    TelegramAlreadyLinkedToAnotherUser,
    UserAlreadyHasTelegramLinked,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.csrf import ensure_trusted_origin
from fanfan.presentation.web.oauth import (
    TELEGRAM_CLIENT_NAME,
    start_telegram_authorization,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

connections_router = APIRouter(prefix="/connections")

# Frontend reads this one-time code from the profile URL and shows a safe toast.
TELEGRAM_LINK_ERROR_QUERY_PARAM = "telegramLinkError"
TELEGRAM_LINK_ERROR_LINKED_TO_ANOTHER_ACCOUNT = "linked_to_another_account"
TELEGRAM_LINK_ERROR_USER_ALREADY_HAS_TELEGRAM = "user_already_has_telegram"


def _build_profile_redirect(error_code: str | None = None) -> RedirectResponse:
    redirect_url = "/profile"

    if error_code is not None:
        redirect_url = (
            f"{redirect_url}?{urlencode({TELEGRAM_LINK_ERROR_QUERY_PARAM: error_code})}"
        )

    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@connections_router.post(
    "/telegram",
    summary="Start Telegram linking",
    description="Redirects the browser to Telegram's OAuth page to begin linking a "
    "Telegram account to the current user. Telegram then calls back to the callback "
    "endpoint to finish.\n\n"
    "Submit this as a same-origin form, not a link: a GET flow-start can be "
    "triggered cross-site by any page, and this one runs against an authenticated "
    "session, so the request initiator is verified.",
    responses={
        303: {"description": "Redirect to Telegram's OAuth authorization page."},
        # Overrides AUTH_RESPONSES' 403 so both causes are documented — the route
        # is authenticated *and* origin-checked.
        403: {
            "model": ErrorMessage,
            "description": "Access denied, or the request did not originate from "
            "a trusted origin.",
        },
    },
)
@inject
async def link_telegram(
    request: Request,
    config: FromDishka[WebConfig],
    oauth: FromDishka[OAuth],
) -> Response:
    ensure_trusted_origin(request, config)
    redirect_uri = request.url_for("link_telegram_callback")
    return await start_telegram_authorization(request, oauth, redirect_uri)


@connections_router.get(
    "/telegram/callback",
    summary="Finish Telegram linking",
    description="OAuth callback for Telegram linking. On success, links the account "
    "and redirects to the profile page. Recoverable errors (already linked to this "
    "or another account) also redirect to the profile page with a "
    "`telegramLinkError` query param the frontend turns into a toast. Invoked by "
    "Telegram, not called directly by the frontend.",
    responses={
        303: {
            "description": "Linking finished. Redirects to the profile page; on a "
            "recoverable error a `telegramLinkError` query param is included."
        },
        400: {"model": ErrorMessage, "description": "Invalid Telegram auth payload."},
    },
)
@inject
async def link_telegram_callback(
    request: Request,
    oauth: FromDishka[OAuth],
    interactor: FromDishka[LinkTelegramAccount],
) -> RedirectResponse:
    telegram: StarletteOAuth2App = oauth.create_client(TELEGRAM_CLIENT_NAME)
    token = await telegram.authorize_access_token(request)
    userinfo = token.get("userinfo", {})
    try:
        await interactor(LinkTelegramAccountInput(user_id=userinfo["id"]))
        return _build_profile_redirect()
    except ValueError as e:
        raise InvalidTelegramAuthPayload from e
    except TelegramAlreadyLinkedToAnotherUser:
        return _build_profile_redirect(TELEGRAM_LINK_ERROR_LINKED_TO_ANOTHER_ACCOUNT)
    except UserAlreadyHasTelegramLinked:
        return _build_profile_redirect(TELEGRAM_LINK_ERROR_USER_ALREADY_HAS_TELEGRAM)


@connections_router.delete(
    "/telegram",
    status_code=204,
    summary="Unlink Telegram account",
    description="Unlinks the Telegram account from the currently authenticated user.",
    responses={
        204: {"description": "Telegram account unlinked successfully."},
        404: {"model": ErrorMessage, "description": "User not found."},
        409: {
            "model": ErrorMessage,
            "description": "Email is required before unlinking.",
        },
    },
)
@inject
async def unlink_telegram_account(
    interactor: FromDishka[UnlinkTelegramAccount],
) -> None:
    await interactor()
