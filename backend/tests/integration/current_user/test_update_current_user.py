from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.current_user.update_current_user import (
    UpdateCurrentUser,
    UpdateCurrentUserInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import UsernameAlreadyTaken, UsernameProfanity
from fanfan.core.models.user import User
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_update_current_user_changes_username(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(UpdateCurrentUser)
    user_gateway = await dishka_request.get(UserGateway)
    login(visitor)

    await interactor(UpdateCurrentUserInput(username="newname"))

    reloaded = await user_gateway.get_by_id(visitor.id)
    assert reloaded is not None
    assert reloaded.username == Username("newname")


async def test_update_current_user_unchanged_username_is_noop(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(UpdateCurrentUser)
    user_gateway = await dishka_request.get(UserGateway)
    login(visitor)

    # Passing the current username changes nothing and must not error.
    await interactor(UpdateCurrentUserInput(username=visitor.username))

    reloaded = await user_gateway.get_by_id(visitor.id)
    assert reloaded is not None
    assert reloaded.username == visitor.username


async def test_update_current_user_rejects_profane_username(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(UpdateCurrentUser)
    user_gateway = await dishka_request.get(UserGateway)
    login(visitor)

    # Usernames are public, so the real profanity filter must reject this one.
    with pytest.raises(UsernameProfanity):
        await interactor(UpdateCurrentUserInput(username="fuck"))

    reloaded = await user_gateway.get_by_id(visitor.id)
    assert reloaded is not None
    assert reloaded.username == visitor.username


async def test_update_current_user_rejects_username_taken_by_another(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(UpdateCurrentUser)
    user_gateway = await dishka_request.get(UserGateway)

    other = User(
        id=generate_user_id(),
        username=Username("takenname"),
        email=None,
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(other)
    await uow.commit()
    login(visitor)

    with pytest.raises(UsernameAlreadyTaken):
        await interactor(UpdateCurrentUserInput(username="takenname"))

    reloaded = await user_gateway.get_by_id(visitor.id)
    assert reloaded is not None
    assert reloaded.username == visitor.username
