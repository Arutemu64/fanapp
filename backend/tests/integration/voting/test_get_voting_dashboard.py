from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.voting.get_voting_dashboard import (
    GetVotingDashboard,
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


async def _add_nomination(
    nomination_gateway: NominationGateway,
    cosplay2_id: int,
    *,
    is_votable: bool = True,
) -> Nomination:
    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=cosplay2_id,
        code=f"dashboard-{cosplay2_id}",
        title=f"Номинация {cosplay2_id}",
        is_votable=is_votable,
    )
    await nomination_gateway.add(nomination)
    return nomination


async def _add_participant(
    participant_gateway: ParticipantGateway,
    nomination: Nomination,
    cosplay2_id: int,
    voting_number: int,
) -> Participant:
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=cosplay2_id,
        title=f"Участник {cosplay2_id}",
        nomination_id=nomination.id,
        voting_number=voting_number,
    )
    await participant_gateway.add(participant)
    return participant


async def _add_votes(
    user_gateway: UserGateway,
    vote_gateway: VoteGateway,
    participant: Participant,
    count: int,
) -> None:
    # Each vote needs a distinct real voter (votes FK users, and the unique
    # (user_id, participant_id) forbids one voter counting twice). Key the username
    # off the full id — uuid7's leading bits are the shared millisecond timestamp,
    # so a short prefix collides for voters created in the same tick.
    for _ in range(count):
        voter_id = UserId(uuid7())
        voter = User(
            id=voter_id,
            username=Username(f"voter_{voter_id.hex}"),
            hashed_password=None,
            role=UserRole.VISITOR,
        )
        await user_gateway.add(voter)
        await vote_gateway.add(
            Vote(
                id=generate_vote_id(),
                user_id=voter.id,
                participant_id=participant.id,
            )
        )


async def test_reports_leader_and_totals_per_nomination(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    user_gateway = await dishka_request.get(UserGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    interactor = await dishka_request.get(GetVotingDashboard)
    login(voting_manager)

    nomination = await _add_nomination(nomination_gateway, cosplay2_id=4000)
    leader = await _add_participant(
        participant_gateway, nomination, cosplay2_id=4001, voting_number=1
    )
    runner_up = await _add_participant(
        participant_gateway, nomination, cosplay2_id=4002, voting_number=2
    )
    await _add_votes(user_gateway, vote_gateway, leader, 3)
    await _add_votes(user_gateway, vote_gateway, runner_up, 1)
    await uow.commit()

    result = await interactor()

    contender = next(n for n in result.nominations if n.id == nomination.id)
    assert contender.leader is not None
    assert contender.leader.participant_id == leader.id
    assert contender.leader.votes_count == 3
    assert contender.total_votes == 4


async def test_nomination_without_votes_has_no_leader(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    interactor = await dishka_request.get(GetVotingDashboard)
    login(voting_manager)

    nomination = await _add_nomination(nomination_gateway, cosplay2_id=4010)
    # A participant exists, but nobody has voted — there is no honest leader.
    await _add_participant(
        participant_gateway, nomination, cosplay2_id=4011, voting_number=1
    )
    await uow.commit()

    result = await interactor()

    contender = next(n for n in result.nominations if n.id == nomination.id)
    assert contender.leader is None
    assert contender.total_votes == 0


async def test_excludes_non_votable_nominations(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    nomination_gateway = await dishka_request.get(NominationGateway)
    interactor = await dishka_request.get(GetVotingDashboard)
    login(voting_manager)

    non_votable = await _add_nomination(
        nomination_gateway, cosplay2_id=4020, is_votable=False
    )
    await uow.commit()

    result = await interactor()

    assert all(n.id != non_votable.id for n in result.nominations)


async def test_reports_contest_pool_size(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    user_gateway = await dishka_request.get(UserGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    interactor = await dishka_request.get(GetVotingDashboard)
    login(voting_manager)

    first_nom = await _add_nomination(nomination_gateway, cosplay2_id=4030)
    first_participant = await _add_participant(
        participant_gateway, first_nom, cosplay2_id=4031, voting_number=1
    )
    second_nom = await _add_nomination(nomination_gateway, cosplay2_id=4032)
    second_participant = await _add_participant(
        participant_gateway, second_nom, cosplay2_id=4033, voting_number=1
    )

    # Two members who each voted in every votable nomination form the pool.
    for i in range(2):
        member = User(
            id=UserId(uuid7()),
            username=Username(f"pool_member_{i}"),
            hashed_password=None,
            role=UserRole.VISITOR,
        )
        await user_gateway.add(member)
        for participant in (first_participant, second_participant):
            await vote_gateway.add(
                Vote(
                    id=generate_vote_id(),
                    user_id=member.id,
                    participant_id=participant.id,
                )
            )
    await uow.commit()

    result = await interactor()

    assert result.contest_pool_size == 2


async def test_requires_voting_manage(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(GetVotingDashboard)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor()
