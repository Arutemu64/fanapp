from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.voting.check_voting_contest_entry import (
    CheckVotingContestEntry,
    CheckVotingContestEntryInput,
)
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.user_flags import UserFlagGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.models.user import User
from fanfan.core.models.user_flag import UserFlag
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id
from fanfan.core.vo.user import UserId
from fanfan.core.vo.user_flag import (
    UserFlagName,
    generate_user_flag_id,
)
from fanfan.core.vo.vote import generate_vote_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_votable_nomination_with_participant(
    nomination_gateway: NominationGateway,
    participant_gateway: ParticipantGateway,
    cosplay2_id: int,
) -> Participant:
    """Create one votable nomination and a participant a user can vote for."""
    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=cosplay2_id,
        code=f"contest-entry-{cosplay2_id}",
        title=f"Тестовая номинация {cosplay2_id}",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=cosplay2_id + 1,
        title=f"Тестовый участник {cosplay2_id}",
        nomination_id=nomination.id,
        voting_number=1,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(participant)
    return participant


async def _add_vote(
    vote_gateway: VoteGateway,
    user_id: UserId,
    participant: Participant,
) -> None:
    # Construct the vote directly (not Vote.create) so setup does not record a
    # VoteCreated event — this interactor is triggered *after* a vote changes.
    await vote_gateway.add(
        Vote(
            id=generate_vote_id(),
            user_id=user_id,
            participant_id=participant.id,
        )
    )


async def test_sets_flag_when_user_voted_in_all_votable_nominations(
    dishka_request: AsyncContainer,
    visitor: User,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CheckVotingContestEntry)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    user_flag_gateway = await dishka_request.get(UserFlagGateway)

    first = await _add_votable_nomination_with_participant(
        nomination_gateway, participant_gateway, cosplay2_id=3000
    )
    second = await _add_votable_nomination_with_participant(
        nomination_gateway, participant_gateway, cosplay2_id=3002
    )
    await _add_vote(vote_gateway, visitor.id, first)
    await _add_vote(vote_gateway, visitor.id, second)
    await uow.commit()

    await interactor(CheckVotingContestEntryInput(user_id=visitor.id))

    assert (
        await user_flag_gateway.get_by_user(
            user_id=visitor.id, flag_name=UserFlagName.VOTING_CONTEST
        )
        is not None
    )


async def test_does_not_set_flag_when_some_nominations_are_unvoted(
    dishka_request: AsyncContainer,
    visitor: User,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CheckVotingContestEntry)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    user_flag_gateway = await dishka_request.get(UserFlagGateway)

    first = await _add_votable_nomination_with_participant(
        nomination_gateway, participant_gateway, cosplay2_id=3010
    )
    # Two votable nominations, but the user has only voted in one of them.
    await _add_votable_nomination_with_participant(
        nomination_gateway, participant_gateway, cosplay2_id=3012
    )
    await _add_vote(vote_gateway, visitor.id, first)
    await uow.commit()

    await interactor(CheckVotingContestEntryInput(user_id=visitor.id))

    assert (
        await user_flag_gateway.get_by_user(
            user_id=visitor.id, flag_name=UserFlagName.VOTING_CONTEST
        )
        is None
    )


async def test_drops_flag_when_user_no_longer_voted_in_all_nominations(
    dishka_request: AsyncContainer,
    visitor: User,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CheckVotingContestEntry)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    user_flag_gateway = await dishka_request.get(UserFlagGateway)

    first = await _add_votable_nomination_with_participant(
        nomination_gateway, participant_gateway, cosplay2_id=3020
    )
    # A second votable nomination the user has not voted in — the previously
    # earned flag is now stale (e.g. this nomination was just made votable, or
    # the user cancelled a vote).
    await _add_votable_nomination_with_participant(
        nomination_gateway, participant_gateway, cosplay2_id=3022
    )
    await _add_vote(vote_gateway, visitor.id, first)
    await user_flag_gateway.add(
        UserFlag(
            id=generate_user_flag_id(),
            name=UserFlagName.VOTING_CONTEST,
            user_id=visitor.id,
        )
    )
    await uow.commit()

    await interactor(CheckVotingContestEntryInput(user_id=visitor.id))

    assert (
        await user_flag_gateway.get_by_user(
            user_id=visitor.id, flag_name=UserFlagName.VOTING_CONTEST
        )
        is None
    )


async def test_keeps_flag_when_user_still_voted_in_all_nominations(
    dishka_request: AsyncContainer,
    visitor: User,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CheckVotingContestEntry)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    user_flag_gateway = await dishka_request.get(UserFlagGateway)

    participant = await _add_votable_nomination_with_participant(
        nomination_gateway, participant_gateway, cosplay2_id=3030
    )
    await _add_vote(vote_gateway, visitor.id, participant)
    await user_flag_gateway.add(
        UserFlag(
            id=generate_user_flag_id(),
            name=UserFlagName.VOTING_CONTEST,
            user_id=visitor.id,
        )
    )
    await uow.commit()

    await interactor(CheckVotingContestEntryInput(user_id=visitor.id))

    assert (
        await user_flag_gateway.get_by_user(
            user_id=visitor.id, flag_name=UserFlagName.VOTING_CONTEST
        )
        is not None
    )


async def test_only_affects_the_given_user(
    dishka_request: AsyncContainer,
    visitor: User,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CheckVotingContestEntry)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    user_flag_gateway = await dishka_request.get(UserFlagGateway)

    participant = await _add_votable_nomination_with_participant(
        nomination_gateway, participant_gateway, cosplay2_id=3040
    )
    # The acting user has voted in every votable nomination, but the check runs
    # for a different user who has not — that other user must stay flagless.
    await _add_vote(vote_gateway, visitor.id, participant)
    other_user_id = UserId(uuid7())
    await uow.commit()

    await interactor(CheckVotingContestEntryInput(user_id=other_user_id))

    assert (
        await user_flag_gateway.get_by_user(
            user_id=other_user_id, flag_name=UserFlagName.VOTING_CONTEST
        )
        is None
    )
    # The user who actually qualified was untouched — the check was not run
    # for them, so their flag must not have been created as a side effect.
    assert (
        await user_flag_gateway.get_by_user(
            user_id=visitor.id, flag_name=UserFlagName.VOTING_CONTEST
        )
        is None
    )
