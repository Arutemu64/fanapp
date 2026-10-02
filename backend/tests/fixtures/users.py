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
    Permission,
    generate_user_permission_id,
)
from fanfan.core.vo.ticket import generate_ticket_id
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


async def _org_user_with(
    dishka_request: AsyncContainer, username: str, *permissions: Permission
) -> User:
    """Create and commit an ORG user holding exactly the given permissions."""
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    user = User(
        id=UserId(uuid7()),
        username=Username(username),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(user)
    for permission in permissions:
        await user_permission_gateway.add(
            UserPermission(
                id=generate_user_permission_id(),
                permission=permission,
                user_id=user.id,
            )
        )
    await uow.commit()
    return user


@pytest_asyncio.fixture
async def sync_operator(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted sync:run.
    """
    return await _org_user_with(dishka_request, "sync_operator", Permission.SYNC_RUN)


@pytest_asyncio.fixture
async def superuser(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted the wildcard "*" (passes every permission check).
    """
    return await _org_user_with(dishka_request, "superuser", Permission.WILDCARD)


@pytest_asyncio.fixture
async def demo_seeder(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted demo:seed.
    """
    return await _org_user_with(dishka_request, "demo_seeder", Permission.DEMO_SEED)


@pytest_asyncio.fixture
async def settings_editor(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted settings:manage.
    """
    return await _org_user_with(
        dishka_request, "settings_editor", Permission.SETTINGS_MANAGE
    )


@pytest_asyncio.fixture
async def voting_manager(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted voting:manage.
    """
    return await _org_user_with(
        dishka_request, "voting_manager", Permission.VOTING_MANAGE
    )


@pytest_asyncio.fixture
async def schedule_editor(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted schedule:manage and schedule:import.
    """
    return await _org_user_with(
        dishka_request,
        "schedule_editor",
        Permission.SCHEDULE_MANAGE,
        Permission.SCHEDULE_IMPORT,
    )


@pytest_asyncio.fixture
async def feedback_reader(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted feedback:read.
    """
    return await _org_user_with(
        dishka_request, "feedback_reader", Permission.FEEDBACK_READ
    )


@pytest_asyncio.fixture
async def users_reader(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted users:read.
    """
    return await _org_user_with(dishka_request, "users_reader", Permission.USERS_READ)
