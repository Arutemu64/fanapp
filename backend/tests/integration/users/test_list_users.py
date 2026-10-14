from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.user import UserListFilter
from fanfan.application.interactors.users.list_users import ListUsers, ListUsersInput
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.ticket import generate_ticket_id
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
    role: UserRole = UserRole.VISITOR,
) -> User:
    user = User(
        id=UserId(uuid7()),
        username=Username(username),
        hashed_password=None,
        role=role,
        email=Email(email) if email else None,
    )
    await user_gateway.add(user)
    return user


def _first_page(
    limit: int = 100, user_filter: UserListFilter | None = None
) -> ListUsersInput:
    return ListUsersInput(
        pagination=CursorPagination(limit=limit),
        user_filter=user_filter or UserListFilter(),
    )


async def test_lists_users_with_total(
    dishka_request: AsyncContainer,
    users_reader: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    user_gateway = await dishka_request.get(UserGateway)
    interactor = await dishka_request.get(ListUsers)
    login(users_reader)

    await _add_user(user_gateway, username="alice_list")
    await _add_user(user_gateway, username="bob_list")
    await uow.commit()

    result = await interactor(_first_page())

    usernames = {u.username for u in result.users}
    assert {"alice_list", "bob_list", "users_reader"} <= usernames
    assert result.total == len(result.users)
    assert result.next_cursor is None


async def test_search_matches_username_email_and_ticket(
    dishka_request: AsyncContainer,
    users_reader: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    user_gateway = await dishka_request.get(UserGateway)
    ticket_gateway = await dishka_request.get(TicketGateway)
    interactor = await dishka_request.get(ListUsers)
    login(users_reader)

    await _add_user(user_gateway, username="searchtarget_user")
    await _add_user(user_gateway, username="other_user", email="findme@example.com")
    ticket_holder = await _add_user(user_gateway, username="ticket_holder")
    await ticket_gateway.add(
        Ticket(
            id=generate_ticket_id(),
            barcode="FAN-SEARCHABLE-42",
            role=UserRole.VISITOR,
            used_by_user_id=ticket_holder.id,
            issued_by_user_id=None,
            ticketscloud_ticket_id=None,
        )
    )
    await uow.commit()

    async def usernames_for(search: str) -> list[str]:
        result = await interactor(
            _first_page(user_filter=UserListFilter(search=search))
        )
        assert result.total == len(result.users)
        return [u.username for u in result.users]

    assert await usernames_for("searchtarget") == ["searchtarget_user"]
    assert await usernames_for("findme@") == ["other_user"]
    assert await usernames_for("searchable-42") == ["ticket_holder"]


async def test_filters_by_role_and_ticket(
    dishka_request: AsyncContainer,
    users_reader: User,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    user_gateway = await dishka_request.get(UserGateway)
    interactor = await dishka_request.get(ListUsers)
    login(users_reader)

    await _add_user(user_gateway, username="filter_helper", role=UserRole.HELPER)
    await uow.commit()

    helpers = await interactor(
        _first_page(user_filter=UserListFilter(role=UserRole.HELPER))
    )
    assert [u.username for u in helpers.users] == ["filter_helper"]

    with_ticket = await interactor(
        _first_page(user_filter=UserListFilter(has_ticket=True))
    )
    assert [u.username for u in with_ticket.users] == [visitor_with_ticket.username]

    without_ticket = await interactor(
        _first_page(user_filter=UserListFilter(has_ticket=False))
    )
    usernames = {u.username for u in without_ticket.users}
    assert visitor_with_ticket.username not in usernames
    assert {"filter_helper", "users_reader"} <= usernames


async def test_pages_newest_first_by_cursor(
    dishka_request: AsyncContainer,
    users_reader: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    user_gateway = await dishka_request.get(UserGateway)
    interactor = await dishka_request.get(ListUsers)
    login(users_reader)

    # Search-scoped usernames so the pages hold only these rows, whatever else
    # the shared test DB holds.
    for name in ("page_a", "page_b", "page_c"):
        await _add_user(user_gateway, username=name)
    await uow.commit()

    user_filter = UserListFilter(search="page_")
    first = await interactor(_first_page(limit=2, user_filter=user_filter))
    assert first.next_cursor is not None
    second = await interactor(
        ListUsersInput(
            pagination=CursorPagination.from_token(limit=2, cursor=first.next_cursor),
            user_filter=user_filter,
        )
    )

    assert [u.username for u in first.users] == ["page_c", "page_b"]
    assert [u.username for u in second.users] == ["page_a"]
    assert second.next_cursor is None
    assert first.total == 3
    assert second.total == 3


async def test_requires_users_read(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(ListUsers)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(_first_page(limit=20))
