from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.voting.draw_voting_contest_winner import (
    DrawVotingContestWinner,
)
from fanfan.application.ports.gateways.user_flags import UserFlagGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from fanfan.core.models.user_flag import UserFlag
from fanfan.core.vo.user import UserId, Username, UserRole
from fanfan.core.vo.user_flag import UserFlagName, generate_user_flag_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_flagged_user(
    user_gateway: UserGateway,
    user_flag_gateway: UserFlagGateway,
    username: str,
) -> User:
    user = User(
        id=UserId(uuid7()),
        username=Username(username),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await user_flag_gateway.add(
        UserFlag(
            id=generate_user_flag_id(),
            name=UserFlagName.VOTING_CONTEST,
            user_id=user.id,
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
    user_flag_gateway = await dishka_request.get(UserFlagGateway)
    interactor = await dishka_request.get(DrawVotingContestWinner)
    login(voting_manager)

    first = await _add_flagged_user(user_gateway, user_flag_gateway, "draw_a")
    second = await _add_flagged_user(user_gateway, user_flag_gateway, "draw_b")
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
