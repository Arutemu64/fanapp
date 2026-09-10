from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.voting.add_vote import AddVote, AddVoteInput
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.votes import VoteAlreadyExists
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.models.user import User
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import (
    ParticipantId,
    generate_participant_id,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_add_vote_creates_vote_and_publishes_event(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AddVote)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor_with_ticket)

    # Voting is only available to a user with a linked ticket
    # and the voting setting enabled in the festival config.
    settings = await settings_gateway.get_for_update()
    settings.set_voting_time_range(
        start=datetime(2020, 1, 1, tzinfo=UTC),
        end=datetime(2099, 1, 1, tzinfo=UTC),
    )
    await settings_gateway.save(settings)

    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1001,
        code="add-vote-test",
        title="Тестовая номинация add-vote-test",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2001,
        title="Тестовый участник",
        nomination_id=nomination.id,
        voting_number=1,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(participant)
    await uow.commit()

    result = await interactor(AddVoteInput(participant_id=participant.id))

    saved_vote = await vote_gateway.get_user_vote_by_nomination(
        nomination_id=nomination.id, user_id=visitor_with_ticket.id
    )
    assert saved_vote is not None
    assert saved_vote.id == result.vote_id
    assert saved_vote.user_id == visitor_with_ticket.id
    assert saved_vote.participant_id == participant.id
    # Voting records no domain events, so the outbox must stay empty.
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_add_vote_without_linked_ticket_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AddVote)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor)

    settings = await settings_gateway.get_for_update()
    settings.set_voting_time_range(
        start=datetime(2020, 1, 1, tzinfo=UTC),
        end=datetime(2099, 1, 1, tzinfo=UTC),
    )
    await settings_gateway.save(settings)

    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1002,
        code="add-vote-no-ticket-test",
        title="Тестовая номинация add-vote-no-ticket-test",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2002,
        title="Тестовый участник без билета",
        nomination_id=nomination.id,
        voting_number=1,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(participant)
    await uow.commit()

    with pytest.raises(AccessDenied) as exc_info:
        await interactor(AddVoteInput(participant_id=participant.id))

    assert exc_info.value.details == {"reason": "VOTING_TICKET_REQUIRED"}
    assert (
        await vote_gateway.get_user_vote_by_nomination(
            nomination_id=nomination.id, user_id=visitor.id
        )
        is None
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_add_vote_when_voting_disabled_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AddVote)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor_with_ticket)

    settings = await settings_gateway.get_for_update()
    settings.set_voting_time_range(start=None, end=None)
    await settings_gateway.save(settings)

    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1003,
        code="add-vote-disabled-test",
        title="Тестовая номинация add-vote-disabled-test",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2003,
        title="Тестовый участник при выключенном голосовании",
        nomination_id=nomination.id,
        voting_number=1,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(participant)
    await uow.commit()

    with pytest.raises(AccessDenied) as exc_info:
        await interactor(AddVoteInput(participant_id=participant.id))

    assert exc_info.value.details == {"reason": "VOTING_DISABLED"}
    assert (
        await vote_gateway.get_user_vote_by_nomination(
            nomination_id=nomination.id, user_id=visitor_with_ticket.id
        )
        is None
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_add_vote_for_missing_participant_raises_not_found(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AddVote)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    login(visitor_with_ticket)

    settings = await settings_gateway.get_for_update()
    settings.set_voting_time_range(
        start=datetime(2020, 1, 1, tzinfo=UTC),
        end=datetime(2099, 1, 1, tzinfo=UTC),
    )
    await settings_gateway.save(settings)
    await uow.commit()

    with pytest.raises(ParticipantNotFound):
        await interactor(AddVoteInput(participant_id=ParticipantId(uuid7())))

    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_add_vote_twice_in_same_nomination_raises_already_voted(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AddVote)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor_with_ticket)

    settings = await settings_gateway.get_for_update()
    settings.set_voting_time_range(
        start=datetime(2020, 1, 1, tzinfo=UTC),
        end=datetime(2099, 1, 1, tzinfo=UTC),
    )
    await settings_gateway.save(settings)

    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1004,
        code="add-vote-same-nomination-test",
        title="Тестовая номинация add-vote-same-nomination-test",
        is_votable=True,
    )
    first_participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2004,
        title="Первый участник",
        nomination_id=nomination.id,
        voting_number=1,
    )
    second_participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2005,
        title="Второй участник",
        nomination_id=nomination.id,
        voting_number=2,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(first_participant)
    await participant_gateway.add(second_participant)
    await uow.commit()

    first_result = await interactor(AddVoteInput(participant_id=first_participant.id))
    with pytest.raises(VoteAlreadyExists):
        await interactor(AddVoteInput(participant_id=second_participant.id))

    saved_vote = await vote_gateway.get_user_vote_by_nomination(
        nomination_id=nomination.id, user_id=visitor_with_ticket.id
    )
    assert saved_vote is not None
    assert saved_vote.id == first_result.vote_id
    assert saved_vote.participant_id == first_participant.id
    # Voting records no domain events, so the outbox must stay empty.
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_gateway_add_second_vote_in_same_nomination_raises_already_voted(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    """The DB unique constraint is the backstop, not just the app-level check.

    Calling the gateway directly (bypassing AddVote's get_user_vote_by_nomination
    check) simulates the concurrent race where two requests both see no existing
    vote and both attempt to insert — the constraint must still reject the second.
    """
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor_with_ticket)

    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1007,
        code="add-vote-db-backstop-test",
        title="Тестовая номинация add-vote-db-backstop-test",
        is_votable=True,
    )
    first_participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2008,
        title="Первый участник backstop-теста",
        nomination_id=nomination.id,
        voting_number=1,
    )
    second_participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2009,
        title="Второй участник backstop-теста",
        nomination_id=nomination.id,
        voting_number=2,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(first_participant)
    await participant_gateway.add(second_participant)
    await uow.commit()

    await vote_gateway.add(
        Vote.create(user_id=visitor_with_ticket.id, participant_id=first_participant.id)
    )
    await uow.commit()

    with pytest.raises(VoteAlreadyExists):
        await vote_gateway.add(
            Vote.create(
                user_id=visitor_with_ticket.id, participant_id=second_participant.id
            )
        )


async def test_reassigning_participant_nomination_updates_existing_vote(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    """Cosplay sync can move a participant to a different nomination.

    votes.nomination_id is a denormalised copy backing uq_votes_user_nomination,
    so ParticipantGateway.save must keep it in lockstep — otherwise the
    constraint (and get_user_vote_by_nomination) would keep enforcing the
    participant's *old* nomination, letting a user cast a second effective
    vote in its new one.
    """
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor_with_ticket)

    old_nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1008,
        code="reassign-old-nomination-test",
        title="Старая номинация reassign-теста",
        is_votable=True,
    )
    new_nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1009,
        code="reassign-new-nomination-test",
        title="Новая номинация reassign-теста",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2010,
        title="Переназначаемый участник",
        nomination_id=old_nomination.id,
        voting_number=1,
    )
    await nomination_gateway.add(old_nomination)
    await nomination_gateway.add(new_nomination)
    await participant_gateway.add(participant)
    await uow.commit()

    await vote_gateway.add(
        Vote.create(user_id=visitor_with_ticket.id, participant_id=participant.id)
    )
    await uow.commit()

    reassigned = Participant(
        id=participant.id,
        cosplay2_id=participant.cosplay2_id,
        title=participant.title,
        nomination_id=new_nomination.id,
        voting_number=participant.voting_number,
    )
    await participant_gateway.save(reassigned)
    await uow.commit()

    assert (
        await vote_gateway.get_user_vote_by_nomination(
            nomination_id=old_nomination.id, user_id=visitor_with_ticket.id
        )
        is None
    )
    moved_vote = await vote_gateway.get_user_vote_by_nomination(
        nomination_id=new_nomination.id, user_id=visitor_with_ticket.id
    )
    assert moved_vote is not None
    assert moved_vote.participant_id == participant.id


async def test_add_vote_allows_votes_in_different_nominations(
    dishka_request: AsyncContainer,
    visitor_with_ticket: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AddVote)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    vote_gateway = await dishka_request.get(VoteGateway)
    login(visitor_with_ticket)

    settings = await settings_gateway.get_for_update()
    settings.set_voting_time_range(
        start=datetime(2020, 1, 1, tzinfo=UTC),
        end=datetime(2099, 1, 1, tzinfo=UTC),
    )
    await settings_gateway.save(settings)

    first_nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1005,
        code="add-vote-first-nomination-test",
        title="Первая номинация",
        is_votable=True,
    )
    first_participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2006,
        title="Участник первой номинации",
        nomination_id=first_nomination.id,
        voting_number=1,
    )
    second_nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1006,
        code="add-vote-second-nomination-test",
        title="Вторая номинация",
        is_votable=True,
    )
    second_participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2007,
        title="Участник второй номинации",
        nomination_id=second_nomination.id,
        voting_number=1,
    )
    await nomination_gateway.add(first_nomination)
    await nomination_gateway.add(second_nomination)
    await participant_gateway.add(first_participant)
    await participant_gateway.add(second_participant)
    await uow.commit()

    first_result = await interactor(AddVoteInput(participant_id=first_participant.id))
    second_result = await interactor(AddVoteInput(participant_id=second_participant.id))

    first_vote = await vote_gateway.get_user_vote_by_nomination(
        nomination_id=first_nomination.id, user_id=visitor_with_ticket.id
    )
    second_vote = await vote_gateway.get_user_vote_by_nomination(
        nomination_id=second_nomination.id, user_id=visitor_with_ticket.id
    )
    assert first_vote is not None
    assert first_vote.id == first_result.vote_id
    assert first_vote.participant_id == first_participant.id
    assert second_vote is not None
    assert second_vote.id == second_result.vote_id
    assert second_vote.participant_id == second_participant.id
    # Voting records no domain events, so the outbox must stay empty.
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []
