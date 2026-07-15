from uuid import uuid7

import pytest_asyncio
from dishka import AsyncContainer

from fanfan.application.ports.gateways import (
    UserPermissionGateway,
)
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.permission import (
    PermissionName,
    Permissions,
    generate_user_permission_id,
)
from fanfan.core.vo.ticket import TicketId, generate_ticket_id
from fanfan.core.vo.user import UserId, Username, UserRole


@pytest_asyncio.fixture
async def visitor(dishka_request: AsyncContainer) -> User:
    """
    Create a visitor (user with no special permissions)
    """
    user_gateway = await dishka_request.get(UserGateway)
    uow = await dishka_request.get(UnitOfWork)

    visitor = User(
        id=UserId(uuid7()),
        username=Username("visitor"),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(visitor)
    await uow.commit()
    return visitor


@pytest_asyncio.fixture
async def visitor_with_ticket(dishka_request: AsyncContainer, visitor: User) -> User:
    """
    Create a visitor with a linked ticket.
    """
    ticket_gateway = await dishka_request.get(TicketGateway)
    uow = await dishka_request.get(UnitOfWork)

    await ticket_gateway.add(
        Ticket(
            id=generate_ticket_id(),
            barcode=f"VISITOR-TICKET-{visitor.id}",
            role=UserRole.VISITOR,
            used_by_user_id=visitor.id,
            issued_by_user_id=None,
            ticketscloud_ticket_id=None,
        )
    )
    await uow.commit()
    return visitor


@pytest_asyncio.fixture
async def schedule_editor(dishka_request: AsyncContainer) -> User:
    """
    Create a schedule manager
    """
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    schedule_editor = User(
        id=UserId(uuid7()),
        username=Username("schedule_editor"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(schedule_editor)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=PermissionName(Permissions.SCHEDULE_MANAGE),
            user_id=schedule_editor.id,
        )
    )
    await uow.commit()
    return schedule_editor
