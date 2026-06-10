from collections.abc import Callable
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
from fanfan.core.events.voting import VoteCreated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.votes import VoteAlreadyExists
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.models.user import User
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import (
    ParticipantId,
    generate_participant_id,
)
from tests.integration.conftest import as_outbox

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

    # Голосование доступно только пользователю с привязанным билетом
    # и включённой настройкой фестиваля.
    settings = await settings_gateway.get_for_update()
    settings.set_voting_enabled(True)
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
        values=[],
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
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        VoteCreated(
            vote_id=result.vote_id,
            user_id=visitor_with_ticket.id,
            participant_id=participant.id,
        )
    )


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
    settings.set_voting_enabled(True)
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
        values=[],
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
    settings.set_voting_enabled(False)
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
        values=[],
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
    settings.set_voting_enabled(True)
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
    settings.set_voting_enabled(True)
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
        values=[],
    )
    second_participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2005,
        title="Второй участник",
        nomination_id=nomination.id,
        voting_number=2,
        values=[],
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
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        VoteCreated(
            vote_id=first_result.vote_id,
            user_id=visitor_with_ticket.id,
            participant_id=first_participant.id,
        )
    )


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
    settings.set_voting_enabled(True)
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
        values=[],
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
        values=[],
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
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        VoteCreated(
            vote_id=first_result.vote_id,
            user_id=visitor_with_ticket.id,
            participant_id=first_participant.id,
        ),
        VoteCreated(
            vote_id=second_result.vote_id,
            user_id=visitor_with_ticket.id,
            participant_id=second_participant.id,
        ),
    )
