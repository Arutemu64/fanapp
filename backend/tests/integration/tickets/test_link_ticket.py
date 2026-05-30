import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.tickets.link_ticket import (
    LinkTicket,
    LinkTicketInput,
)
from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.tickets import (
    TicketAlreadyUsed,
    TicketNotFound,
    UserAlreadyHasTicketLinked,
)
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.ticket import generate_ticket_id
from fanfan.core.vo.user import UserRole
from tests.fakes.id_provider import FakeIdProvider

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_link_ticket_successfully(dishka_request: AsyncContainer, visitor: User):
    interactor = await dishka_request.get(LinkTicket)
    user_repo = await dishka_request.get(UserRepository)
    ticket_repo = await dishka_request.get(TicketRepository)
    trx = await dishka_request.get(TransactionManager)
    id_provider = await dishka_request.get(FakeIdProvider)

    ticket = Ticket(
        id=generate_ticket_id(),
        barcode="123456",
        role=UserRole.PARTICIPANT,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    await ticket_repo.add(ticket)
    await trx.commit()

    id_provider.set_current_user_id(visitor.id)

    await interactor(LinkTicketInput(barcode="123456"))

    # Assert user role updated
    saved_user = await user_repo.get_by_id(visitor.id)
    assert saved_user.role == UserRole.PARTICIPANT

    # Assert ticket is used by user
    saved_ticket = await ticket_repo.get_by_barcode("123456")
    assert saved_ticket.is_used_by(visitor.id)


async def test_link_ticket_raises_ticket_not_found(
    dishka_request: AsyncContainer, visitor: User
):
    interactor = await dishka_request.get(LinkTicket)
    id_provider = await dishka_request.get(FakeIdProvider)

    id_provider.set_current_user_id(visitor.id)

    with pytest.raises(TicketNotFound):
        await interactor(LinkTicketInput(barcode="123456"))


async def test_link_ticket_raises_already_used(
    dishka_request: AsyncContainer, visitor: User, schedule_editor: User
):
    interactor = await dishka_request.get(LinkTicket)
    ticket_repo = await dishka_request.get(TicketRepository)
    trx = await dishka_request.get(TransactionManager)
    id_provider = await dishka_request.get(FakeIdProvider)

    ticket = Ticket(
        id=generate_ticket_id(),
        barcode="123456",
        role=UserRole.PARTICIPANT,
        used_by_user_id=schedule_editor.id,  # Used by other user
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    await ticket_repo.add(ticket)
    await trx.commit()

    id_provider.set_current_user_id(visitor.id)

    with pytest.raises(TicketAlreadyUsed):
        await interactor(LinkTicketInput(barcode="123456"))


async def test_link_ticket_raises_when_user_already_has_ticket(
    dishka_request: AsyncContainer, visitor_with_ticket: User
):
    interactor = await dishka_request.get(LinkTicket)
    ticket_repo = await dishka_request.get(TicketRepository)
    trx = await dishka_request.get(TransactionManager)
    id_provider = await dishka_request.get(FakeIdProvider)

    # New ticket to link
    ticket = Ticket(
        id=generate_ticket_id(),
        barcode="123456",
        role=UserRole.PARTICIPANT,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    await ticket_repo.add(ticket)
    await trx.commit()

    id_provider.set_current_user_id(visitor_with_ticket.id)

    with pytest.raises(UserAlreadyHasTicketLinked):
        await interactor(LinkTicketInput(barcode="123456"))
