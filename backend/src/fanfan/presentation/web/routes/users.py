from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.tickets.link_ticket import LinkTicket, LinkTicketCommand
from fanfan.application.users.get_current_user import GetCurrentUser
from fanfan.application.users.update_user import (
    UpdateCurrentUser,
    UpdateCurrentUserCommand,
)
from fanfan.application.users.update_user_settings import (
    UpdateUserSettings,
    UpdateUserSettingsCommand,
)
from fanfan.core.dto.user import CurrentUserDTO
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.tickets import TicketNotFound, UserAlreadyHasTicketLinked
from fanfan.core.exceptions.users import UsernameAlreadyTaken
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
    interactor: FromDishka[GetCurrentUser],
) -> CurrentUserDTO:
    return await interactor()


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
    await interactor(data)


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
