from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.voting.draw_voting_contest_winner import (
    DrawVotingContestWinner,
)
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.models.user import User
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id
from fanfan.core.vo.user import UserId, Username, UserRole
from fanfan.core.vo.vote import generate_vote_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_votable_nomination(
    nomination_gateway: NominationGateway,
    participant_gateway: ParticipantGateway,
    cosplay2_id: int,
) -> Participant:
    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=cosplay2_id,
        code=f"draw-{cosplay2_id}",
        title=f"Номинация {cosplay2_id}",
        is_votable=True,
    )
    await nomination_gateway.add(nomination)
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=cosplay2_id + 1,
        title=f"Участник {cosplay2_id}",
        nomination_id=nomination.id,
        voting_number=1,
    )
    await participant_gateway.add(participant)
    return participant


async def _add_voter(
    user_gateway: UserGateway,
    vote_gateway: VoteGateway,
    username: str,
    participants: list[Participant],
) -> User:
    # A voter is in the prize-draw pool once they have voted in every votable
    # nomination — one vote per participant listed here.
    user = User(
        id=UserId(uuid7()),
        username=Username(username),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    for participant in participants:
        await vote_gateway.add(
            Vote(
                id=generate_vote_id(),
                user_id=user.id,
                participant_id=participant.id,
            )
        )
    return user


async def test_draws_a_winner_from_the_pool(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    user_gateway = await dishka_request.get(UserGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    interactor = await dishka_request.get(DrawVotingContestWinner)
    login(voting_manager)

    first_nom = await _add_votable_nomination(
        nomination_gateway, participant_gateway, cosplay2_id=5000
    )
    second_nom = await _add_votable_nomination(
        nomination_gateway, participant_gateway, cosplay2_id=5010
    )
    every_nomination = [first_nom, second_nom]

    first = await _add_voter(user_gateway, vote_gateway, "draw_a", every_nomination)
    second = await _add_voter(user_gateway, vote_gateway, "draw_b", every_nomination)
    # Voted in only one of the two nominations — not eligible for the draw.
    await _add_voter(user_gateway, vote_gateway, "draw_partial", [first_nom])
    await uow.commit()

    result = await interactor()

    assert result.pool_size == 2
    assert result.winner is not None
    assert result.winner.id in {first.id, second.id}


async def test_empty_pool_returns_no_winner(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(DrawVotingContestWinner)
    login(voting_manager)

    result = await interactor()

    assert result.pool_size == 0
    assert result.winner is None


async def test_requires_voting_manage(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(DrawVotingContestWinner)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor()
