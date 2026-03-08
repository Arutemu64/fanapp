from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request
from starlette import status

from fanfan.application.tickets.link_ticket import LinkTicket, LinkTicketCommand
from fanfan.application.users.get_current_user import GetCurrentUser
from fanfan.application.users.get_current_user_social_accounts import (
    GetCurrentUserSocialAccounts,
)
from fanfan.application.users.link_telegram_account import (
    LinkTelegramAccount,
    LinkTelegramAccountCommand,
)
from fanfan.application.users.unlink_telegram_account import UnlinkTelegramAccount
from fanfan.application.users.update_user import (
    UpdateCurrentUser,
    UpdateCurrentUserCommand,
)
from fanfan.application.users.update_user_settings import (
    UpdateUserSettings,
    UpdateUserSettingsCommand,
)
from fanfan.core.dto.user import CurrentUserDTO, UserSocialAccountDTO
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.tickets import TicketNotFound, UserAlreadyHasTicketLinked
from fanfan.core.exceptions.users import (
    TelegramAlreadyConnected,
    TelegramAlreadyLinked,
    TelegramCannotBeUnlinkedWithoutEmail,
    UserHasNoEmail,
    UsernameAlreadyTaken,
    UserNotFound,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

users_router = APIRouter(tags=["Users"], prefix="/users")


@users_router.get(
    "/me",
    summary="Get current user",
    description="Retrieves the currently authenticated user's profile information.",
    responses={
        200: {
            "model": CurrentUserDTO,
            "description": "User profile retrieved successfully.",
        },
    },
)
@inject
async def get_current_user(
    request: Request,
    interactor: FromDishka[GetCurrentUser],
) -> CurrentUserDTO:
    return await interactor()


@users_router.get(
    "/me/social-accounts",
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
    interactor: FromDishka[GetCurrentUserSocialAccounts],
) -> list[UserSocialAccountDTO]:
    try:
        return await interactor()
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@users_router.patch(
    "/me",
    summary="Update current user",
    description="Updates the currently authenticated user's profile information.",
    responses={
        200: {"description": "User updated successfully."},
        409: {"model": ErrorMessage, "description": "Username already taken."},
    },
)
@inject
async def update_current_user(
    data: UpdateCurrentUserCommand,
    interactor: FromDishka[UpdateCurrentUser],
) -> None:
    try:
        await interactor(data)
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UsernameAlreadyTaken as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@users_router.patch(
    "/me/settings",
    summary="Update current user settings",
    description="Updates the currently authenticated user's profile settings.",
    responses={
        200: {"description": "User settings updated successfully."},
    },
)
@inject
async def update_current_user_settings(
    data: UpdateUserSettingsCommand,
    interactor: FromDishka[UpdateUserSettings],
) -> None:
    try:
        await interactor(data)
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@users_router.post(
    "/me/social-accounts/telegram",
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
async def link_telegram_account(
    data: LinkTelegramAccountCommand,
    interactor: FromDishka[LinkTelegramAccount],
) -> None:
    try:
        await interactor(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось подтвердить Telegram",
        ) from e
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except (TelegramAlreadyLinked, TelegramAlreadyConnected) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@users_router.delete(
    "/me/social-accounts/telegram",
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except (UserHasNoEmail, TelegramCannotBeUnlinkedWithoutEmail) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@users_router.post(
    "/me/ticket",
    summary="Link ticket",
    description="Links provided ticket to current user.",
    responses={
        200: {"description": "Ticket linked successfully."},
        404: {"model": ErrorMessage, "description": "Ticket not found."},
        409: {
            "model": ErrorMessage,
            "description": "User already has a ticket linked.",
        },
    },
)
@inject
async def link_ticket(
    data: LinkTicketCommand,
    interactor: FromDishka[LinkTicket],
) -> None:
    try:
        return await interactor(data)
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except TicketNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UserAlreadyHasTicketLinked as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
