from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.tickets.link_ticket import (
    LinkTicket,
    LinkTicketInput,
)
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.tickets import (
    TicketAlreadyUsed,
    TicketNotFound,
    UserAlreadyHasTicketLinked,
)
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.ticket import generate_ticket_id
from fanfan.core.vo.user import UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_link_ticket_accepts_org_code_typed_in_lowercase(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(LinkTicket)
    ticket_gateway = await dishka_request.get(TicketGateway)

    ticket = Ticket(
        id=generate_ticket_id(),
        barcode="FAN-7K4Q9M",
        role=UserRole.VISITOR,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    await ticket_gateway.add(ticket)
    await uow.commit()

    login(visitor)

    await interactor(LinkTicketInput(barcode=" fan-7k4q9m "))

    saved_ticket = await ticket_gateway.get_by_barcode("FAN-7K4Q9M")
    assert saved_ticket is not None
    assert saved_ticket.is_used_by(visitor.id)


async def test_link_ticket_prefers_exact_vendor_spelling(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(LinkTicket)
    ticket_gateway = await dishka_request.get(TicketGateway)

    # A vendor barcode that happens to look like an org code, next to the org
    # ticket its folded form would match: the exact spelling must win.
    vendor = Ticket(
        id=generate_ticket_id(),
        barcode="FAN-o0",
        role=UserRole.VISITOR,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    folded = Ticket(
        id=generate_ticket_id(),
        barcode="FAN-00",
        role=UserRole.VISITOR,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    await ticket_gateway.add(vendor)
    await ticket_gateway.add(folded)
    await uow.commit()

    login(visitor)

    await interactor(LinkTicketInput(barcode="FAN-o0"))

    saved_vendor = await ticket_gateway.get_by_barcode("FAN-o0")
    saved_folded = await ticket_gateway.get_by_barcode("FAN-00")
    assert saved_vendor is not None
    assert saved_vendor.is_used_by(visitor.id)
    assert saved_folded is not None
    assert not saved_folded.is_used


async def test_link_ticket_successfully(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(LinkTicket)
    user_gateway = await dishka_request.get(UserGateway)
    ticket_gateway = await dishka_request.get(TicketGateway)

    ticket = Ticket(
        id=generate_ticket_id(),
        barcode="123456",
        role=UserRole.PARTICIPANT,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    await ticket_gateway.add(ticket)
    await uow.commit()

    login(visitor)

    await interactor(LinkTicketInput(barcode="123456"))

    saved_user = await user_gateway.get_by_id(visitor.id)
    assert saved_user is not None
    assert saved_user.role == UserRole.PARTICIPANT

    saved_ticket = await ticket_gateway.get_by_barcode("123456")
    assert saved_ticket is not None
    assert saved_ticket.is_used_by(visitor.id)


async def test_link_ticket_raises_ticket_not_found(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(LinkTicket)

    login(visitor)

    with pytest.raises(TicketNotFound):
        await interactor(LinkTicketInput(barcode="123456"))


async def test_link_ticket_raises_already_used(
    dishka_request: AsyncContainer,
    visitor: User,
    schedule_editor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(LinkTicket)
    ticket_gateway = await dishka_request.get(TicketGateway)

    ticket = Ticket(
        id=generate_ticket_id(),
        barcode="123456",
        role=UserRole.PARTICIPANT,
        used_by_user_id=schedule_editor.id,  # Used by other user
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    await ticket_gateway.add(ticket)
    await uow.commit()

    login(visitor)

    with pytest.raises(TicketAlreadyUsed):
        await interactor(LinkTicketInput(barcode="123456"))


async def test_link_ticket_raises_when_user_already_has_ticket(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(LinkTicket)
    ticket_gateway = await dishka_request.get(TicketGateway)

    # New ticket to link
    ticket = Ticket(
        id=generate_ticket_id(),
        barcode="123456",
        role=UserRole.PARTICIPANT,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )
    await ticket_gateway.add(ticket)
    await uow.commit()

    login(visitor_with_ticket)

    with pytest.raises(UserAlreadyHasTicketLinked):
        await interactor(LinkTicketInput(barcode="123456"))
