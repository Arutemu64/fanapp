from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.users.unlink_user_ticket import (
    UnlinkUserTicket,
    UnlinkUserTicketInput,
)
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.tickets import TicketNotLinked
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.models.user import User
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id
from fanfan.core.vo.user import UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_frees_ticket_drops_votes_and_keeps_role(
    dishka_request: AsyncContainer,
    users_manager: User,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(UnlinkUserTicket)
    ticket_gateway = await dishka_request.get(TicketGateway)
    user_gateway = await dishka_request.get(UserGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)

    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1301,
        code="unlink-ticket-test",
        title="Тестовая номинация unlink-ticket-test",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2301,
        title="Тестовый участник",
        nomination_id=nomination.id,
        voting_number=1,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(participant)
    await vote_gateway.add(
        Vote.create(user_id=visitor_with_ticket.id, participant_id=participant.id)
    )
    await uow.commit()
    ticket = await ticket_gateway.get_by_user_id(visitor_with_ticket.id)
    assert ticket is not None

    login(users_manager)
    result = await interactor(UnlinkUserTicketInput(user_id=visitor_with_ticket.id))

    assert result.deleted_votes == 1
    assert await vote_gateway.count_user_votes(visitor_with_ticket.id) == 0
    assert await ticket_gateway.get_by_user_id(visitor_with_ticket.id) is None
    freed = await ticket_gateway.get_by_barcode(barcode=ticket.barcode)
    assert freed is not None
    assert freed.used_by_user_id is None
    user = await user_gateway.get_by_id(visitor_with_ticket.id)
    assert user is not None
    assert user.role is UserRole.VISITOR


async def test_user_without_ticket_is_refused(
    dishka_request: AsyncContainer,
    users_manager: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(UnlinkUserTicket)
    login(users_manager)

    with pytest.raises(TicketNotLinked):
        await interactor(UnlinkUserTicketInput(user_id=visitor.id))


async def test_requires_users_manage(
    dishka_request: AsyncContainer,
    users_reader: User,
    visitor_with_ticket: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(UnlinkUserTicket)
    login(users_reader)

    with pytest.raises(AccessDenied):
        await interactor(UnlinkUserTicketInput(user_id=visitor_with_ticket.id))
