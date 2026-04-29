from uuid import uuid7

import pytest_asyncio
from dishka import AsyncContainer

from fanfan.application.ports.repositories import (
    PermissionRepository,
    UserPermissionRepository,
)
from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permissions
from fanfan.core.vo.user import UserId, Username, UserRole


@pytest_asyncio.fixture
async def visitor(dishka_request: AsyncContainer) -> User:
    """
    Create a visitor (user with no special permissions)
    """
    user_repo = await dishka_request.get(UserRepository)
    trx = await dishka_request.get(TransactionManager)

    visitor = User(
        id=UserId(uuid7()),
        username=Username("visitor"),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_repo.add(visitor)
    await trx.commit()
    return visitor


@pytest_asyncio.fixture
async def visitor_with_ticket(dishka_request: AsyncContainer, visitor: User) -> User:
    """
    Create a visitor with a linked ticket.
    """
    ticket_repo = await dishka_request.get(TicketRepository)
    trx = await dishka_request.get(TransactionManager)

    await ticket_repo.add(
        Ticket(
            barcode=f"VISITOR-TICKET-{visitor.id}",
            role=UserRole.VISITOR,
            used_by_user_id=visitor.id,
            issued_by_user_id=None,
            ticketscloud_ticket_id=None,
        )
    )
    await trx.commit()
    return visitor


@pytest_asyncio.fixture
async def schedule_editor(dishka_request: AsyncContainer) -> User:
    """
    Create a schedule manager
    """
    user_repo = await dishka_request.get(UserRepository)
    permission_repo = await dishka_request.get(PermissionRepository)
    user_permission_repo = await dishka_request.get(UserPermissionRepository)
    trx = await dishka_request.get(TransactionManager)

    schedule_editor = User(
        id=UserId(uuid7()),
        username=Username("schedule_editor"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_repo.add(schedule_editor)
    schedule_manage_permission = await permission_repo.get_by_name(
        Permissions.SCHEDULE_MANAGE
    )
    await user_permission_repo.add(
        UserPermission(
            permission_id=schedule_manage_permission.id,
            user_id=schedule_editor.id,
            object_type=None,
            object_id=None,
        )
    )
    await trx.commit()
    return schedule_editor
