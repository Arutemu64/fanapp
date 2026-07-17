from collections.abc import Callable
from uuid import uuid7

import pytest
import pytest_asyncio
from dishka import AsyncContainer

from fanfan.application.interactors.tickets.generate_tickets import (
    GenerateTickets,
    GenerateTicketsInput,
)
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission, generate_user_permission_id
from fanfan.core.vo.user import UserId, Username, UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


@pytest_asyncio.fixture
async def ticket_issuer(dishka_request: AsyncContainer) -> User:
    """Create an organizer granted the tickets:generate permission."""
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    issuer = User(
        id=UserId(uuid7()),
        username=Username("ticket_issuer"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(issuer)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.TICKETS_GENERATE,
            user_id=issuer.id,
        )
    )
    await uow.commit()
    return issuer


async def test_generate_tickets_creates_unique_persisted_tickets(
    dishka_request: AsyncContainer,
    ticket_issuer: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(GenerateTickets)
    ticket_gateway = await dishka_request.get(TicketGateway)

    login(ticket_issuer)

    result = await interactor(GenerateTicketsInput(role=UserRole.HELPER, amount=5))

    assert len(result.barcodes) == 5
    assert len(set(result.barcodes)) == 5
    assert all(barcode.startswith("FAN-") for barcode in result.barcodes)

    # Every returned barcode is persisted with the chosen role, marked as issued
    # by the actor, and not yet used.
    for barcode in result.barcodes:
        saved = await ticket_gateway.get_by_barcode(barcode)
        assert saved is not None
        assert saved.role == UserRole.HELPER
        assert saved.issued_by_user_id == ticket_issuer.id
        assert saved.is_used is False


async def test_generate_tickets_requires_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(GenerateTickets)

    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(GenerateTicketsInput(role=UserRole.HELPER, amount=1))
