from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Body, Path, Query

from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.user import UserDetailsDTO, UserListFilter
from fanfan.application.interactors.presence.get_online_users_count import (
    GetOnlineUsersCount,
    OnlineUsersCountOutput,
)
from fanfan.application.interactors.users.get_user import GetUser, GetUserInput
from fanfan.application.interactors.users.list_users import (
    ListUsers,
    ListUsersInput,
    ListUsersOutput,
)
from fanfan.application.interactors.users.set_user_permission import (
    SetUserPermission,
    SetUserPermissionInput,
)
from fanfan.application.interactors.users.set_user_role import (
    SetUserRole,
    SetUserRoleInput,
)
from fanfan.application.interactors.users.unlink_user_ticket import (
    UnlinkUserTicket,
    UnlinkUserTicketInput,
)
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId, UserRole
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.schemas.users import UserListQuery
from fanfan.presentation.web.security import session_security

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@users_router.get(
    "/",
    summary="List users",
    description="Newest-first, filterable directory of all users. Search matches a "
    "case-insensitive substring of the username, email or ticket number; the "
    "filters combine with AND. Requires users:read.",
    responses={
        200: {"description": "Users retrieved successfully."},
        403: {"model": ErrorMessage, "description": "Missing users:read."},
    },
)
@inject
async def list_users(
    interactor: FromDishka[ListUsers],
    query: Annotated[UserListQuery, Query()],
) -> ListUsersOutput:
    data = ListUsersInput(
        pagination=CursorPagination.from_token(limit=query.limit, cursor=query.cursor),
        user_filter=UserListFilter(
            search=query.search, role=query.role, has_ticket=query.has_ticket
        ),
    )
    return await interactor(data)


# Declared before /{user_id} so the literal path wins over the UUID path param,
# which would otherwise try to parse "online-count" as a user id.
@users_router.get(
    "/online-count",
    summary="Count online users",
    description="How many users hold a live connection right now, for the "
    "organiser dashboard. Approximate and ephemeral. Any authenticated user.",
    responses={
        200: {"description": "Online user count retrieved successfully."},
    },
)
@inject
async def count_online_users(
    interactor: FromDishka[GetOnlineUsersCount],
) -> OnlineUsersCountOutput:
    return await interactor()


@users_router.get(
    "/{user_id}",
    summary="Get user details",
    description="Profile basics, linked external accounts and granted permissions "
    "for one user. Requires users:read.",
    responses={
        200: {"description": "User details retrieved successfully."},
        403: {"model": ErrorMessage, "description": "Missing users:read."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def get_user(
    user_id: Annotated[UserId, Path(description="ID of the user to look up.")],
    interactor: FromDishka[GetUser],
) -> UserDetailsDTO:
    return await interactor(GetUserInput(user_id=user_id))


@users_router.put(
    "/{user_id}/role",
    status_code=204,
    summary="Change a user's role",
    description="Sets another user's role. Requires users:manage; an organiser "
    "cannot change their own role.",
    responses={
        204: {"description": "Role changed."},
        400: {"model": ErrorMessage, "description": "Tried to change own role."},
        403: {"model": ErrorMessage, "description": "Missing users:manage."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def set_user_role(
    user_id: Annotated[UserId, Path(description="ID of the user to change.")],
    role: Annotated[UserRole, Body(embed=True)],
    interactor: FromDishka[SetUserRole],
) -> None:
    await interactor(SetUserRoleInput(user_id=user_id, role=role))


@users_router.put(
    "/{user_id}/permissions/{permission}",
    status_code=204,
    summary="Grant a permission",
    description="Grants one permission to another user; idempotent. Requires the "
    "superuser grant. The superuser grant itself is CLI-only.",
    responses={
        204: {"description": "Permission granted."},
        400: {
            "model": ErrorMessage,
            "description": "Own permissions, or the superuser grant.",
        },
        403: {"model": ErrorMessage, "description": "Missing the superuser grant."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def grant_user_permission(
    user_id: Annotated[UserId, Path(description="ID of the user to change.")],
    permission: Annotated[Permission, Path(description="Permission to grant.")],
    interactor: FromDishka[SetUserPermission],
) -> None:
    await interactor(
        SetUserPermissionInput(user_id=user_id, permission=permission, granted=True)
    )


@users_router.delete(
    "/{user_id}/permissions/{permission}",
    status_code=204,
    summary="Revoke a permission",
    description="Revokes one permission from another user; idempotent. Requires "
    "the superuser grant. The superuser grant itself is CLI-only.",
    responses={
        204: {"description": "Permission revoked."},
        400: {
            "model": ErrorMessage,
            "description": "Own permissions, or the superuser grant.",
        },
        403: {"model": ErrorMessage, "description": "Missing the superuser grant."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def revoke_user_permission(
    user_id: Annotated[UserId, Path(description="ID of the user to change.")],
    permission: Annotated[Permission, Path(description="Permission to revoke.")],
    interactor: FromDishka[SetUserPermission],
) -> None:
    await interactor(
        SetUserPermissionInput(user_id=user_id, permission=permission, granted=False)
    )


@users_router.delete(
    "/{user_id}/ticket",
    status_code=204,
    summary="Unlink a user's ticket",
    description="Frees the user's ticket for linking again and deletes the user's "
    "votes, which the ticket entitled. The role is left unchanged. Idempotent. "
    "Requires users:manage.",
    responses={
        204: {"description": "Ticket unlinked and votes deleted."},
        403: {"model": ErrorMessage, "description": "Missing users:manage."},
    },
)
@inject
async def unlink_user_ticket(
    user_id: Annotated[UserId, Path(description="ID of the user to change.")],
    interactor: FromDishka[UnlinkUserTicket],
) -> None:
    await interactor(UnlinkUserTicketInput(user_id=user_id))
