from collections.abc import Callable
from uuid import uuid7

import pytest
import pytest_asyncio
from dishka import AsyncContainer

from fanfan.application.dto.ticket import TicketListFilter
from fanfan.application.interactors.tickets.generate_tickets import (
    GenerateTickets,
    GenerateTicketsInput,
)
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.tickets import TicketBatchAlreadyExists
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.ticket_batch import TicketBatch
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission, generate_user_permission_id
from fanfan.core.vo.ticket import TicketBatchId
from fanfan.core.vo.user import UserId, Username, UserRole


def _generate(role: UserRole, amount: int) -> GenerateTicketsInput:
    return GenerateTicketsInput(
        batch_id=TicketBatchId(uuid7()), role=role, amount=amount
    )


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


@pytest_asyncio.fixture
async def ticket_issuer(dishka_request: AsyncContainer) -> User:
    """Create an organizer granted the tickets:manage permission."""
    user_gateway = await dishka_request.get(UserGateway)
    user_permission_gateway = await dishka_request.get(UserPermissionGateway)
    uow = await dishka_request.get(UnitOfWork)

    issuer = User(
        id=UserId(uuid7()),
        username=Username("ticket_issuer"),
        hashed_password=None,
        role=UserRole.ORGANIZER,
    )
    await user_gateway.add(issuer)
    await user_permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.TICKETS_MANAGE,
            user_id=issuer.id,
        )
    )
    await uow.commit()
    return issuer


async def test_generate_tickets_creates_unique_persisted_tickets(
    dishka_request: AsyncContainer,
    ticket_issuer: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(GenerateTickets)
    ticket_gateway = await dishka_request.get(TicketGateway)

    login(ticket_issuer)

    result = await interactor(_generate(UserRole.VOLUNTEER, 5))

    assert len(result.barcodes) == 5
    assert len(set(result.barcodes)) == 5
    assert all(barcode.startswith("FAN-") for barcode in result.barcodes)

    for barcode in result.barcodes:
        saved = await ticket_gateway.get_by_barcode(barcode)
        assert saved is not None
        assert saved.role == UserRole.VOLUNTEER
        assert saved.issued_by_user_id == ticket_issuer.id
        assert saved.is_used is False


async def test_generate_tickets_requires_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(GenerateTickets)

    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(_generate(UserRole.VOLUNTEER, 1))


async def test_generate_tickets_replay_returns_the_batch_without_new_tickets(
    dishka_request: AsyncContainer,
    ticket_issuer: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(GenerateTickets)
    ticket_gateway = await dishka_request.get(TicketGateway)
    login(ticket_issuer)
    data = _generate(UserRole.VOLUNTEER, 3)

    first = await interactor(data)
    second = await interactor(data)

    assert sorted(second.barcodes) == sorted(first.barcodes)
    assert await ticket_gateway.count_tickets(ticket_filter=TicketListFilter()) == 3


async def test_generate_tickets_with_a_taken_id_raises_already_exists(
    dishka_request: AsyncContainer,
    ticket_issuer: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(GenerateTickets)
    login(ticket_issuer)
    data = _generate(UserRole.VOLUNTEER, 3)
    await interactor(data)

    with pytest.raises(TicketBatchAlreadyExists):
        await interactor(data.model_copy(update={"amount": 4}))


async def test_overlapping_generate_loses_the_insert_race_with_already_exists(
    dishka_request: AsyncContainer,
    ticket_issuer: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(GenerateTickets)
    ticket_gateway = await dishka_request.get(TicketGateway)
    login(ticket_issuer)
    data = _generate(UserRole.VOLUNTEER, 2)
    await interactor(data)

    racer = TicketBatch.issue(
        batch_id=data.batch_id,
        role=data.role,
        amount=data.amount,
        issued_by_user_id=ticket_issuer.id,
    )
    with pytest.raises(TicketBatchAlreadyExists):
        await ticket_gateway.add_batch(racer)


async def test_add_batch_redraws_a_barcode_that_is_already_taken(
    dishka_request: AsyncContainer,
    ticket_issuer: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(GenerateTickets)
    ticket_gateway = await dishka_request.get(TicketGateway)
    login(ticket_issuer)
    taken = (await interactor(_generate(UserRole.VOLUNTEER, 1))).barcodes[0]

    batch = TicketBatch.issue(
        batch_id=TicketBatchId(uuid7()),
        role=UserRole.VOLUNTEER,
        amount=2,
        issued_by_user_id=ticket_issuer.id,
    )
    batch.tickets[0].barcode = taken
    await ticket_gateway.add_batch(batch)

    assert taken not in batch.barcodes
    saved = await ticket_gateway.get_batch(batch.id)
    assert saved is not None
    assert sorted(saved.barcodes) == sorted(batch.barcodes)
