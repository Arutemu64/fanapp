from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request
from starlette import status
from starlette.responses import RedirectResponse

from fanfan.application.dto.user import UserSocialAccountDTO
from fanfan.application.interactors.current_user.get_current_user_social_ids import (
    GetCurrentUserSocialIds,
)
from fanfan.application.interactors.current_user.link_telegram_account import (
    LinkTelegramAccount,
    LinkTelegramAccountInput,
)
from fanfan.application.interactors.current_user.unlink_telegram_account import (
    UnlinkTelegramAccount,
)
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import (
    TelegramAlreadyLinkedToAnotherUser,
    TelegramCannotBeUnlinkedWithoutEmail,
    UserAlreadyHasTelegramLinked,
    UserHasNoEmail,
    UserNotFound,
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


@connections_router.get(
    "/",
    summary="Get current user social accounts",
    description="Retrieves the currently authenticated user's linked social accounts.",
    responses={
        200: {
            "model": list[UserSocialAccountDTO],
            "description": "User social accounts retrieved successfully.",
        },
        401: {"model": ErrorMessage, "description": "User not authenticated."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def get_current_user_social_accounts(
    interactor: FromDishka[GetCurrentUserSocialIds],
) -> list[UserSocialAccountDTO]:
    try:
        return await interactor()
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e


@connections_router.get(
    "/telegram",
    summary="Link Telegram account",
    description="Links a Telegram account to the currently authenticated user.",
    responses={
        200: {"description": "Telegram account linked successfully."},
        400: {"model": ErrorMessage, "description": "Invalid Telegram auth payload."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
        404: {"model": ErrorMessage, "description": "User not found."},
        409: {
            "model": ErrorMessage,
            "description": "Telegram is already linked to this or another account.",
        },
    },
)
@inject
async def link_telegram(
    request: Request,
    oauth: FromDishka[OAuth],
) -> None:
    telegram: StarletteOAuth2App = oauth.create_client("telegram")
    redirect_uri = request.url_for("link_telegram_callback")
    return await telegram.authorize_redirect(request, redirect_uri)


@connections_router.get(
    "/telegram/callback",
    summary="Link Telegram account",
    description="Links a Telegram account to the currently authenticated user.",
    responses={
        200: {"description": "Telegram account linked successfully."},
        400: {"model": ErrorMessage, "description": "Invalid Telegram auth payload."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
        404: {"model": ErrorMessage, "description": "User not found."},
        409: {
            "model": ErrorMessage,
            "description": "Telegram is already linked to this or another account.",
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
    token = await telegram.authorize_access_token(request)
    userinfo = token.get("userinfo", {})
    try:
        await interactor(LinkTelegramAccountInput(user_id=userinfo["id"]))
        return _build_profile_redirect()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось подтвердить Telegram",
        ) from e
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except TelegramAlreadyLinkedToAnotherUser:
        return _build_profile_redirect(TELEGRAM_LINK_ERROR_LINKED_TO_ANOTHER_ACCOUNT)
    except UserAlreadyHasTelegramLinked:
        return _build_profile_redirect(TELEGRAM_LINK_ERROR_USER_ALREADY_HAS_TELEGRAM)


@connections_router.delete(
    "/telegram",
    summary="Unlink Telegram account",
    description="Unlinks the Telegram account from the currently authenticated user.",
    responses={
        200: {"description": "Telegram account unlinked successfully."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
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
    try:
        await interactor()
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except (UserHasNoEmail, TelegramCannotBeUnlinkedWithoutEmail) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=e.message
        ) from e
