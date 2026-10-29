import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.voting.get_voting_nomination import (
    GetVotingNomination,
    GetVotingNominationInput,
)
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.nominations import NominationNotFound
from fanfan.core.models.nomination import Nomination
from fanfan.core.vo.nomination import NominationCode, generate_nomination_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_nomination(
    nomination_gateway: NominationGateway,
    cosplay2_id: int,
    code: str,
    *,
    is_votable: bool,
) -> Nomination:
    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=cosplay2_id,
        code=code,
        title=f"Номинация {code}",
        is_votable=is_votable,
    )
    await nomination_gateway.add(nomination)
    return nomination


async def test_returns_votable_nomination(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    nomination_gateway = await dishka_request.get(NominationGateway)
    interactor = await dishka_request.get(GetVotingNomination)
    nomination = await _add_nomination(
        nomination_gateway, 6000, "voting-nomination-open", is_votable=True
    )
    await uow.commit()

    result = await interactor(
        GetVotingNominationInput(nomination_code=NominationCode(nomination.code))
    )

    assert result.id == nomination.id


async def test_non_votable_nomination_is_not_found(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    nomination_gateway = await dishka_request.get(NominationGateway)
    interactor = await dishka_request.get(GetVotingNomination)
    nomination = await _add_nomination(
        nomination_gateway, 6001, "voting-nomination-hidden", is_votable=False
    )
    await uow.commit()

    with pytest.raises(NominationNotFound):
        await interactor(
            GetVotingNominationInput(nomination_code=NominationCode(nomination.code))
        )
