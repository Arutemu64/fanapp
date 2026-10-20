from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.user import User
from fanfan.core.vo.user import UserId, Username, UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_a_taken_number_is_redrawn(
    dishka_request: AsyncContainer, visitor: User
) -> None:
    user_gateway = await dishka_request.get(UserGateway)
    uow = await dishka_request.get(UnitOfWork)

    newcomer = User(
        id=UserId(uuid7()),
        username=Username("newcomer"),
        hashed_password=None,
        role=UserRole.VISITOR,
        number=visitor.number,
    )
    await user_gateway.add(newcomer)
    await uow.commit()

    assert newcomer.number != visitor.number
    stored = await user_gateway.get_by_number(newcomer.number)
    assert stored is not None
    assert stored.id == newcomer.id
