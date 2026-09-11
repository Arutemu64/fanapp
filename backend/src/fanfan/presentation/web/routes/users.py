from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Path, Query

from fanfan.application.dto.page import Pagination
from fanfan.application.dto.user import UserDetailsDTO
from fanfan.application.interactors.presence.get_online_users_count import (
    GetOnlineUsersCount,
    OnlineUsersCountOutput,
)
from fanfan.application.interactors.users.get_user import GetUser, GetUserInput
from fanfan.application.interactors.users.list_users import (
    ListUsers,
    ListUsersInput,
    ListUsersResult,
)
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
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
    description="Paginated, searchable directory of all users. Search matches a "
    "case-insensitive substring of the username or email. Requires users:read.",
    responses={
        200: {
            "model": ListUsersResult,
            "description": "Users retrieved successfully.",
        },
        403: {"model": ErrorMessage, "description": "Missing users:read."},
    },
)
@inject
async def list_users(
    interactor: FromDishka[ListUsers],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> ListUsersResult:
    data = ListUsersInput(
        pagination=Pagination(limit=limit, offset=offset), search=search
    )
    return await interactor(data)


@users_router.get(
    "/online-count",
    summary="Count online users",
    description="How many users hold a live connection right now, for the "
    "organiser dashboard. Approximate and ephemeral. Requires users:read.",
    responses={
        200: {
            "model": OnlineUsersCountOutput,
            "description": "Online user count retrieved successfully.",
        },
        403: {"model": ErrorMessage, "description": "Missing users:read."},
    },
)
@inject
async def count_online_users(
    interactor: FromDishka[GetOnlineUsersCount],
) -> OnlineUsersCountOutput:
    # Declared before /{user_id} so the literal path wins over the UUID path
    # param, which would otherwise try to parse "online-count" as a user id.
    return await interactor()


@users_router.get(
    "/{user_id}",
    summary="Get user details",
    description="Profile basics and linked external accounts for one user. "
    "Requires users:read.",
    responses={
        200: {
            "model": UserDetailsDTO,
            "description": "User details retrieved successfully.",
        },
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
