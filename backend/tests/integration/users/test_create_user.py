import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.users.create_user import (
    CreateUser,
    CreateUserInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.core.exceptions.users import UserAlreadyExists, UsernameProfanity
from fanfan.core.vo.user import UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

_PASSWORD = "supersecret123"


async def test_creates_a_user_with_a_hashed_password(
    dishka_request: AsyncContainer,
):
    create_user = await dishka_request.get(CreateUser)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    created = await create_user(
        CreateUserInput(username="tester", password=_PASSWORD, role=UserRole.ORG)
    )

    stored = await user_gateway.get_by_username("tester")
    assert stored is not None
    assert stored.id == created.id
    assert stored.role is UserRole.ORG
    # The password is stored hashed, never in the clear, and verifies.
    assert stored.hashed_password is not None
    assert stored.hashed_password != _PASSWORD
    assert password_hasher.verify(_PASSWORD, stored.hashed_password)


async def test_duplicate_username_is_rejected(
    dishka_request: AsyncContainer,
):
    create_user = await dishka_request.get(CreateUser)

    await create_user(
        CreateUserInput(username="tester", password=_PASSWORD, role=UserRole.ORG)
    )
    with pytest.raises(UserAlreadyExists):
        await create_user(
            CreateUserInput(username="tester", password=_PASSWORD, role=UserRole.ORG)
        )


async def test_profane_username_is_rejected(
    dishka_request: AsyncContainer,
):
    create_user = await dishka_request.get(CreateUser)

    with pytest.raises(UsernameProfanity):
        await create_user(
            CreateUserInput(username="fuck", password=_PASSWORD, role=UserRole.ORG)
        )
