from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.users.list_users import ListUsers, ListUsersInput
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import UserId, Username, UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_user(
    user_gateway: UserGateway,
    *,
    username: str,
    email: str | None = None,
) -> User:
    user = User(
        id=UserId(uuid7()),
        username=Username(username),
        hashed_password=None,
        role=UserRole.VISITOR,
        email=Email(email) if email else None,
    )
    await user_gateway.add(user)
    return user


async def test_lists_matching_users_with_total(
    dishka_request: AsyncContainer,
    users_reader: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    user_gateway = await dishka_request.get(UserGateway)
    interactor = await dishka_request.get(ListUsers)
    login(users_reader)

    await _add_user(user_gateway, username="alice_list")
    await _add_user(user_gateway, username="bob_list")
    await uow.commit()

    result = await interactor(
        ListUsersInput(pagination=Pagination(limit=100, offset=0))
    )

    # The reader itself plus the two added users are all in the unfiltered set;
    # total counts everyone, not just the returned page.
    usernames = {u.username for u in result.users}
    assert {"alice_list", "bob_list", "users_reader"} <= usernames
    assert result.total == len(result.users)


async def test_search_matches_username_and_email(
    dishka_request: AsyncContainer,
    users_reader: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    user_gateway = await dishka_request.get(UserGateway)
    interactor = await dishka_request.get(ListUsers)
    login(users_reader)

    await _add_user(user_gateway, username="searchtarget_user")
    await _add_user(user_gateway, username="other_user", email="findme@example.com")
    await uow.commit()

    by_username = await interactor(
        ListUsersInput(
            pagination=Pagination(limit=100, offset=0), search="searchtarget"
        )
    )
    assert [u.username for u in by_username.users] == ["searchtarget_user"]
    assert by_username.total == 1

    by_email = await interactor(
        ListUsersInput(pagination=Pagination(limit=100, offset=0), search="findme@")
    )
    assert [u.username for u in by_email.users] == ["other_user"]
    assert by_email.total == 1


async def test_pagination_limits_and_offsets(
    dishka_request: AsyncContainer,
    users_reader: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    user_gateway = await dishka_request.get(UserGateway)
    interactor = await dishka_request.get(ListUsers)
    login(users_reader)

    # Distinct search-scoped usernames so ordering is deterministic regardless of
    # what other rows the shared test DB holds.
    for name in ("page_a", "page_b", "page_c"):
        await _add_user(user_gateway, username=name)
    await uow.commit()

    first = await interactor(
        ListUsersInput(pagination=Pagination(limit=2, offset=0), search="page_")
    )
    second = await interactor(
        ListUsersInput(pagination=Pagination(limit=2, offset=2), search="page_")
    )

    assert [u.username for u in first.users] == ["page_a", "page_b"]
    assert [u.username for u in second.users] == ["page_c"]
    assert first.total == 3
    assert second.total == 3


async def test_requires_users_read(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(ListUsers)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(ListUsersInput(pagination=Pagination(limit=20, offset=0)))
