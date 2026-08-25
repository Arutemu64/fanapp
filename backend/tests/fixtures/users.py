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
async def sync_operator(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted sync:run.
    """
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    sync_operator = User(
        id=UserId(uuid7()),
        username=Username("sync_operator"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(sync_operator)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.SYNC_RUN,
            user_id=sync_operator.id,
        )
    )
    await uow.commit()
    return sync_operator


@pytest_asyncio.fixture
async def demo_seeder(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted demo:seed.
    """
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    demo_seeder = User(
        id=UserId(uuid7()),
        username=Username("demo_seeder"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(demo_seeder)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.DEMO_SEED,
            user_id=demo_seeder.id,
        )
    )
    await uow.commit()
    return demo_seeder


@pytest_asyncio.fixture
async def settings_editor(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted settings:manage.
    """
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    settings_editor = User(
        id=UserId(uuid7()),
        username=Username("settings_editor"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(settings_editor)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.SETTINGS_MANAGE,
            user_id=settings_editor.id,
        )
    )
    await uow.commit()
    return settings_editor


@pytest_asyncio.fixture
async def voting_manager(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted voting:manage.
    """
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    voting_manager = User(
        id=UserId(uuid7()),
        username=Username("voting_manager"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(voting_manager)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.VOTING_MANAGE,
            user_id=voting_manager.id,
        )
    )
    await uow.commit()
    return voting_manager


@pytest_asyncio.fixture
async def schedule_editor(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted schedule:manage and schedule:import.
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
    for permission in (Permission.SCHEDULE_MANAGE, Permission.SCHEDULE_IMPORT):
        await user_permission_gateway.add(
            UserPermission(
                id=generate_user_permission_id(),
                permission=permission,
                user_id=schedule_editor.id,
            )
        )
    await uow.commit()
    return schedule_editor


@pytest_asyncio.fixture
async def feedback_reader(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted feedback:read.
    """
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    feedback_reader = User(
        id=UserId(uuid7()),
        username=Username("feedback_reader"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(feedback_reader)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.FEEDBACK_READ,
            user_id=feedback_reader.id,
        )
    )
    await uow.commit()
    return feedback_reader


@pytest_asyncio.fixture
async def users_reader(dishka_request: AsyncContainer) -> User:
    """
    Create a user granted users:read.
    """
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    users_reader = User(
        id=UserId(uuid7()),
        username=Username("users_reader"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(users_reader)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.USERS_READ,
            user_id=users_reader.id,
        )
    )
    await uow.commit()
    return users_reader
