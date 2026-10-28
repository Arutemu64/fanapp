from collections.abc import Awaitable, Callable
from http import HTTPStatus

from dishka import AsyncContainer
from httpx2 import AsyncClient

from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.models.user import User
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id

OPEN_VOTING = {
    "voting_starts_at": "2020-01-01T00:00:00Z",
    "voting_ends_at": "2099-01-01T00:00:00Z",
}


async def _add_participant(dishka_request: AsyncContainer) -> Participant:
    nomination_gateway = await dishka_request.get(NominationGateway)
    participant_gateway = await dishka_request.get(ParticipantGateway)
    uow = await dishka_request.get(UnitOfWork)
    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=1001,
        code="http-vote",
        title="Косплей-дефиле",
        is_votable=True,
    )
    participant = Participant(
        id=generate_participant_id(),
        cosplay2_id=2001,
        title="Участник",
        nomination_id=nomination.id,
        voting_number=1,
    )
    await nomination_gateway.add(nomination)
    await participant_gateway.add(participant)
    await uow.commit()
    return participant


async def test_attendee_votes_once_after_an_organizer_opens_voting(
    dishka_request: AsyncContainer,
    client: AsyncClient,
    voting_manager: User,
    visitor_with_ticket: User,
    sign_in: Callable[[User], Awaitable[None]],
) -> None:
    participant = await _add_participant(dishka_request)
    await sign_in(voting_manager)
    opened = await client.put("/voting/time-range", json=OPEN_VOTING)
    assert opened.status_code == HTTPStatus.NO_CONTENT

    await sign_in(visitor_with_ticket)
    vote = {"participant_id": str(participant.id)}
    cast = await client.post("/voting/votes", json=vote)
    assert cast.status_code == HTTPStatus.CREATED
    vote_id = cast.json()["vote_id"]
    assert cast.headers["location"].endswith(f"/voting/votes/{vote_id}")

    again = await client.post("/voting/votes", json=vote)
    assert again.status_code == HTTPStatus.CONFLICT
    assert again.json()["code"] == "ALREADY_VOTED_IN_THIS_NOMINATION"


async def test_attendee_cannot_open_voting(
    client: AsyncClient,
    visitor: User,
    sign_in: Callable[[User], Awaitable[None]],
) -> None:
    await sign_in(visitor)

    response = await client.put("/voting/time-range", json=OPEN_VOTING)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.headers["content-type"] == "application/problem+json"


async def test_attendee_cannot_vote_once_an_organizer_takes_the_nomination_out(
    dishka_request: AsyncContainer,
    client: AsyncClient,
    voting_manager: User,
    visitor_with_ticket: User,
    sign_in: Callable[[User], Awaitable[None]],
) -> None:
    participant = await _add_participant(dishka_request)
    await sign_in(voting_manager)
    await client.put("/voting/time-range", json=OPEN_VOTING)
    taken_out = await client.patch(
        f"/voting/nominations/{participant.nomination_id}",
        json={"is_votable": False},
    )
    assert taken_out.status_code == HTTPStatus.NO_CONTENT

    await sign_in(visitor_with_ticket)
    cast = await client.post(
        "/voting/votes", json={"participant_id": str(participant.id)}
    )

    assert cast.status_code == HTTPStatus.FORBIDDEN
    assert cast.json()["code"] == "NOMINATION_NOT_VOTABLE"


async def test_nomination_patch_refuses_null_votable(
    dishka_request: AsyncContainer,
    client: AsyncClient,
    voting_manager: User,
    sign_in: Callable[[User], Awaitable[None]],
) -> None:
    participant = await _add_participant(dishka_request)
    await sign_in(voting_manager)

    response = await client.patch(
        f"/voting/nominations/{participant.nomination_id}",
        json={"is_votable": None},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
