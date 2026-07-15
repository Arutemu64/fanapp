from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.voting.cancel_vote import (
    CancelVote,
    CancelVoteInput,
)
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.voting import VoteDeleted
from fanfan.core.exceptions.votes import VoteNotFound
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.models.user import User
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id
from fanfan.core.vo.user import UserId, Username, UserRole
from fanfan.core.vo.vote import VoteId, generate_vote_id
from tests.integration.conftest import as_outbox

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_cancel_vote_deletes_vote_and_publishes_event(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CancelVote)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor_with_ticket)

    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1101,
        code="cancel-vote-test",
        title="Тестовая номинация cancel-vote-test",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2101,
        title="Тестовый участник",
        nomination_id=nomination.id,
        voting_number=1,
    )
    # Construct the vote directly (not Vote.create) so setup doesn't enqueue a
    # VoteCreated event and pollute the outbox assertion below.
    vote = Vote(
        id=generate_vote_id(),
        user_id=visitor_with_ticket.id,
        participant_id=participant.id,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(participant)
    await vote_gateway.add(vote)
    await uow.commit()

    await interactor(CancelVoteInput(vote_id=vote.id))

    assert await vote_gateway.get(vote.id) is None
    assert (
        await vote_gateway.get_user_vote_by_nomination(
            nomination_id=nomination.id, user_id=visitor_with_ticket.id
        )
        is None
    )
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        VoteDeleted(
            vote_id=vote.id,
            user_id=visitor_with_ticket.id,
            participant_id=participant.id,
        )
    )


async def test_cancel_vote_for_missing_vote_raises_not_found(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CancelVote)
    login(visitor_with_ticket)

    with pytest.raises(VoteNotFound):
        await interactor(CancelVoteInput(vote_id=VoteId(uuid7())))

    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_cancel_vote_owned_by_another_user_raises_not_found(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CancelVote)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    user_gateway = await dishka_request.get(UserGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor_with_ticket)

    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1102,
        code="cancel-vote-other-user-test",
        title="Тестовая номинация cancel-vote-other-user-test",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2102,
        title="Тестовый участник чужого голоса",
        nomination_id=nomination.id,
        voting_number=1,
    )
    other_user = User(
        id=UserId(uuid7()),
        username=Username("other_visitor"),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    # The vote belongs to another user; the acting user must not be able to
    # cancel it, and its existence must not leak (VoteNotFound, not AccessDenied).
    other_vote = Vote(
        id=generate_vote_id(),
        user_id=other_user.id,
        participant_id=participant.id,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(participant)
    await user_gateway.add(other_user)
    await vote_gateway.add(other_vote)
    await uow.commit()

    with pytest.raises(VoteNotFound):
        await interactor(CancelVoteInput(vote_id=other_vote.id))

    assert await vote_gateway.get(other_vote.id) is not None
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []
