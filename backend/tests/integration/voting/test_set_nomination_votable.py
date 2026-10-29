from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.voting.set_nomination_votable import (
    SetNominationVotable,
    SetNominationVotableInput,
)
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.nominations import NominationNotFound
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.user import User
from fanfan.core.vo.nomination import generate_nomination_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_nomination(
    nomination_gateway: NominationGateway, cosplay2_id: int, *, is_votable: bool
) -> Nomination:
    nomination = Nomination(
        id=generate_nomination_id(),
        cosplay2_id=cosplay2_id,
        code=f"votable-{cosplay2_id}",
        title=f"Номинация {cosplay2_id}",
        is_votable=is_votable,
    )
    await nomination_gateway.add(nomination)
    return nomination


@pytest.mark.parametrize("is_votable", [True, False])
async def test_sets_votable_flag(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
    is_votable: bool,  # noqa: FBT001
) -> None:
    nomination_gateway = await dishka_request.get(NominationGateway)
    interactor = await dishka_request.get(SetNominationVotable)
    login(voting_manager)
    nomination = await _add_nomination(
        nomination_gateway, cosplay2_id=5000, is_votable=not is_votable
    )
    await uow.commit()

    await interactor(
        SetNominationVotableInput(nomination_id=nomination.id, is_votable=is_votable)
    )

    saved = await nomination_gateway.get(nomination.id)
    assert saved is not None
    assert saved.is_votable is is_votable


async def test_unknown_nomination_raises_not_found(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetNominationVotable)
    login(voting_manager)

    with pytest.raises(NominationNotFound):
        await interactor(
            SetNominationVotableInput(
                nomination_id=generate_nomination_id(), is_votable=True
            )
        )


async def test_requires_voting_manage(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetNominationVotable)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(
            SetNominationVotableInput(
                nomination_id=generate_nomination_id(), is_votable=True
            )
        )
