from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.users.get_user import GetUser, GetUserInput
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.social_identity import (
    SocialProvider,
    generate_social_identity_id,
)
from fanfan.core.vo.user import UserId, Username, UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_returns_basics_and_social_links(
    dishka_request: AsyncContainer,
    users_reader: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    user_gateway = await dishka_request.get(UserGateway)
    social_gateway = await dishka_request.get(SocialIdentityGateway)
    interactor = await dishka_request.get(GetUser)
    login(users_reader)

    user = User(
        id=UserId(uuid7()),
        username=Username("detailed_user"),
        hashed_password=None,
        role=UserRole.VISITOR,
        email=Email("detailed@example.com"),
    )
    await user_gateway.add(user)
    await social_gateway.add(
        SocialIdentity(
            id=generate_social_identity_id(),
            user_id=user.id,
            provider=SocialProvider.TELEGRAM,
            subject="tg-subject",
            provider_user_id=987654321,
        )
    )
    await uow.commit()

    result = await interactor(GetUserInput(user_id=user.id))

    assert result.id == user.id
    assert result.username == "detailed_user"
    assert result.email == "detailed@example.com"
    assert len(result.social_links) == 1
    link = result.social_links[0]
    assert link.provider is SocialProvider.TELEGRAM
    # provider_user_id is serialised as a string to survive the JS number range.
    assert link.id == "987654321"


async def test_missing_user_raises_not_found(
    dishka_request: AsyncContainer,
    users_reader: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(GetUser)
    login(users_reader)

    with pytest.raises(UserNotFound):
        await interactor(GetUserInput(user_id=UserId(uuid7())))


async def test_requires_users_read(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(GetUser)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(GetUserInput(user_id=visitor.id))
