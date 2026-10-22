from collections.abc import Callable
from uuid import uuid7

import pytest
import pytest_asyncio
from dishka import AsyncContainer

from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.ticket import TCloudEventRoleDTO, TicketListFilter
from fanfan.application.interactors.tickets.list_tickets import (
    ListTickets,
    ListTicketsInput,
)
from fanfan.application.interactors.tickets.tcloud_event_roles import (
    GetTCloudEventRoles,
    SetTCloudEventRoles,
    SetTCloudEventRolesInput,
)
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.settings import TCloudEventRolesChanged
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission, generate_user_permission_id
from fanfan.core.vo.user import UserId, Username, UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_user(
    dishka_request: AsyncContainer, username: str, permission: Permission | None
) -> User:
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    user = User(
        id=UserId(uuid7()),
        username=Username(username),
        hashed_password=None,
        role=UserRole.ORGANIZER,
    )
    await user_gateway.add(user)
    if permission is not None:
        await user_permission_gateway.add(
            UserPermission(
                id=generate_user_permission_id(),
                permission=permission,
                user_id=user.id,
            )
        )
    return user


@pytest_asyncio.fixture
async def ticket_manager(dishka_request: AsyncContainer, uow: UnitOfWork) -> User:
    manager = await _add_user(
        dishka_request, "ticket_manager", Permission.TICKETS_MANAGE
    )
    await uow.commit()
    return manager


async def test_list_tickets_pages_newest_first_with_linked_user(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    ticket_manager: User,
    login: Callable[[User], None],
) -> None:
    ticket_gateway = await dishka_request.get(TicketGateway)
    holder = await _add_user(dishka_request, "ticket_holder", None)
    for _ in range(3):
        await ticket_gateway.add_all(
            [Ticket.issue(role=UserRole.VOLUNTEER, issued_by_user_id=ticket_manager.id)]
        )
    linked = Ticket.issue(
        role=UserRole.PARTICIPANT, issued_by_user_id=ticket_manager.id
    )
    linked.set_as_used(holder.id)
    await ticket_gateway.add_all([linked])
    await uow.commit()

    login(ticket_manager)
    interactor = await dishka_request.get(ListTickets)

    first = await interactor(ListTicketsInput(pagination=CursorPagination(limit=2)))

    assert first.total == 4
    assert len(first.tickets) == 2
    assert first.next_cursor is not None
    newest = first.tickets[0]
    assert newest.barcode == linked.barcode
    assert newest.used_by_user_id == holder.id
    assert newest.used_by_username == "ticket_holder"
    assert newest.from_ticketscloud is False

    rest = await interactor(
        ListTicketsInput(
            pagination=CursorPagination.from_token(limit=2, cursor=first.next_cursor)
        )
    )
    assert len(rest.tickets) == 2
    assert rest.next_cursor is None

    found = await interactor(
        ListTicketsInput(
            pagination=CursorPagination(limit=10),
            ticket_filter=TicketListFilter(search=linked.barcode.lower()),
        )
    )
    assert [ticket.id for ticket in found.tickets] == [linked.id]
    assert found.total == 1


async def test_list_tickets_requires_permission(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
) -> None:
    outsider = await _add_user(dishka_request, "outsider", None)
    await uow.commit()
    login(outsider)
    interactor = await dishka_request.get(ListTickets)

    with pytest.raises(AccessDenied):
        await interactor(ListTicketsInput(pagination=CursorPagination(limit=10)))


async def test_set_tcloud_event_roles_round_trips(
    dishka_request: AsyncContainer,
    ticket_manager: User,
    login: Callable[[User], None],
) -> None:
    login(ticket_manager)
    set_roles = await dishka_request.get(SetTCloudEventRoles)
    get_roles = await dishka_request.get(GetTCloudEventRoles)
    event_roles = [
        TCloudEventRoleDTO(event_id="event-a", role=UserRole.PARTICIPANT),
        TCloudEventRoleDTO(event_id="event-b", role=UserRole.VOLUNTEER),
    ]

    saved = await set_roles(
        SetTCloudEventRolesInput(event_roles=event_roles), if_match=None
    )

    result = await get_roles()
    assert result.event_roles == event_roles
    assert result.etag == saved.etag


async def test_set_tcloud_event_roles_against_a_stale_etag_is_refused(
    dishka_request: AsyncContainer,
    ticket_manager: User,
    login: Callable[[User], None],
) -> None:
    login(ticket_manager)
    set_roles = await dishka_request.get(SetTCloudEventRoles)
    get_roles = await dishka_request.get(GetTCloudEventRoles)
    first = TCloudEventRoleDTO(event_id="event-a", role=UserRole.PARTICIPANT)
    second = TCloudEventRoleDTO(event_id="event-b", role=UserRole.VOLUNTEER)

    # Two organizers open the form on the same version and each adds a row.
    read_by_both = (await get_roles()).etag
    await set_roles(
        SetTCloudEventRolesInput(event_roles=[first]),
        if_match=frozenset({read_by_both}),
    )

    # The PUT replaces the whole mapping, so the second save would drop the
    # first organizer's row.
    with pytest.raises(TCloudEventRolesChanged):
        await set_roles(
            SetTCloudEventRolesInput(event_roles=[second]),
            if_match=frozenset({read_by_both}),
        )

    assert (await get_roles()).event_roles == [first]
