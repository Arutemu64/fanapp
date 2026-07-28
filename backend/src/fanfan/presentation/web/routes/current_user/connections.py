import logging
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, OAuthError, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from httpx import HTTPError
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
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.telegram_oauth import (
    TELEGRAM_OAUTH_ERROR_FAILED,
    classify_oauth_error,
    read_telegram_claims,
)

logger = logging.getLogger(__name__)

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


@connections_router.get(
    "/telegram",
    summary="Start Telegram linking",
    description="Redirects the browser to Telegram's OAuth page to begin linking a "
    "Telegram account to the current user. Telegram then calls back to the callback "
    "endpoint to finish.",
    responses={
        302: {"description": "Redirect to Telegram's OAuth authorization page."},
    },
)
@inject
async def link_telegram(
    request: Request,
    oauth: FromDishka[OAuth],
) -> Response:
    telegram: StarletteOAuth2App = oauth.create_client("telegram")
    redirect_uri = request.url_for("link_telegram_callback")

    try:
        return await telegram.authorize_redirect(request, redirect_uri)
    except HTTPError:
        # Building the redirect needs Telegram's discovery document. The registry
        # is APP-scoped so it is fetched once per process — this is the first
        # linking attempt after a restart running into an unreachable Telegram.
        logger.warning("Could not reach Telegram to start account linking")
        return _build_profile_redirect(TELEGRAM_OAUTH_ERROR_FAILED)


@connections_router.get(
    "/telegram/callback",
    summary="Finish Telegram linking",
    description="OAuth callback for Telegram linking. On success, links the account "
    "and redirects to the profile page. Every recoverable error (already linked to "
    "this or another account, cancelled or failed authorization) also redirects to "
    "the profile page with a `telegramLinkError` query param the frontend turns into "
    "a toast. Invoked by Telegram, not called directly by the frontend.",
    responses={
        303: {
            "description": "Linking finished. Redirects to the profile page; on a "
            "recoverable error a `telegramLinkError` query param is included."
        },
    },
)
@inject
async def link_telegram_callback(
    request: Request,
    oauth: FromDishka[OAuth],
    interactor: FromDishka[LinkTelegramAccount],
) -> RedirectResponse:
    telegram: StarletteOAuth2App = oauth.create_client("telegram")

    try:
        token = await telegram.authorize_access_token(request)
        claims = read_telegram_claims(token)
    except OAuthError as e:
        # Declining on Telegram, letting the state expire (Authlib gives it an
        # hour) and re-opening an already-used callback URL all land here. None
        # of them is a server fault, so this stays below warning level.
        logger.info("Telegram linking did not complete", extra={"oauth_error": e.error})
        return _build_profile_redirect(classify_oauth_error(e))
    except InvalidTelegramAuthPayload:
        # Signature-valid token, unusable content — almost always the bot's
        # signing algorithm in BotFather stripping the `profile` scope.
        logger.warning("Telegram ID token carried no usable profile claims")
        return _build_profile_redirect(TELEGRAM_OAUTH_ERROR_FAILED)

    try:
        await interactor(LinkTelegramAccountInput(user_id=claims.id))
    except TelegramAlreadyLinkedToAnotherUser:
        return _build_profile_redirect(TELEGRAM_LINK_ERROR_LINKED_TO_ANOTHER_ACCOUNT)
    except UserAlreadyHasTelegramLinked:
        return _build_profile_redirect(TELEGRAM_LINK_ERROR_USER_ALREADY_HAS_TELEGRAM)

    return _build_profile_redirect()


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
