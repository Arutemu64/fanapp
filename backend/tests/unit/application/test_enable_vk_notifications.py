from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import override

import pytest

from fanfan.application.interactors.current_user.enable_vk_notifications import (
    EnableVkNotifications,
)
from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.ports.vk_messages import VkMessagesPermission
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.notifications import (
    NotificationsCheckTooFast,
    VkMessagesNotAllowed,
)
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.core.exceptions.users import SocialAccountNotLinked
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.social_identity import SocialProvider, generate_social_identity_id
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = pytest.mark.asyncio

VK_USER_ID = 555


class _StubCurrentUser(CurrentUserProvider):
    def __init__(self, user: User) -> None:
        self._user = user

    @override
    async def require_user(self) -> User:
        return self._user


class _StubIdentities(SocialIdentityGateway):
    def __init__(self, identity: SocialIdentity | None) -> None:
        self._identity = identity

    @override
    async def get_by_provider(
        self, user_id: object, provider: SocialProvider
    ) -> SocialIdentity | None:
        return self._identity


class _StubUsers(UserGateway):
    def __init__(self) -> None:
        self.saved: list[User] = []

    @override
    async def save(self, user: User) -> None:
        self.saved.append(user)


class _StubPermission(VkMessagesPermission):
    def __init__(self, *, allowed: bool) -> None:
        self._allowed = allowed
        self.asked: list[int] = []

    @override
    async def is_allowed(self, vk_user_id: int) -> bool:
        self.asked.append(vk_user_id)
        return self._allowed


class _StubUow(UnitOfWork):
    @override
    async def commit(self) -> None:
        pass


class _Cooldown(Cooldown):
    def __init__(self, *, active: bool = False) -> None:
        self._active = active

    @asynccontextmanager
    async def _claim(self) -> AsyncGenerator[None]:
        if self._active:
            raise CooldownActive(retry_after=3)
        yield

    @override
    def claim(self, key: str, seconds: int) -> AbstractAsyncContextManager[None]:
        return self._claim()


def _user() -> User:
    return User(
        id=generate_user_id(),
        username=Username("tester"),
        hashed_password=None,
        role=UserRole.VISITOR,
        settings=UserSettings(receive_vk_notifications=False),
    )


def _identity(user: User) -> SocialIdentity:
    return SocialIdentity(
        id=generate_social_identity_id(),
        user_id=user.id,
        provider=SocialProvider.VK,
        subject=str(VK_USER_ID),
        provider_user_id=VK_USER_ID,
    )


def _interactor(
    user: User,
    *,
    identity: SocialIdentity | None,
    permission: _StubPermission,
    users: _StubUsers | None = None,
    cooldown: _Cooldown | None = None,
) -> EnableVkNotifications:
    return EnableVkNotifications(
        current_user_provider=_StubCurrentUser(user),
        social_identity_gateway=_StubIdentities(identity),
        user_gateway=users or _StubUsers(),
        vk_messages_permission=permission,
        cooldown=cooldown or _Cooldown(),
        uow=_StubUow(),
    )


async def test_turns_vk_on_once_the_community_may_write() -> None:
    user = _user()
    users = _StubUsers()
    permission = _StubPermission(allowed=True)

    await _interactor(
        user, identity=_identity(user), permission=permission, users=users
    )()

    assert permission.asked == [VK_USER_ID]
    assert user.settings.receive_vk_notifications is True
    assert users.saved == [user]


async def test_refuses_while_the_community_may_not_write() -> None:
    user = _user()
    users = _StubUsers()

    with pytest.raises(VkMessagesNotAllowed):
        await _interactor(
            user,
            identity=_identity(user),
            permission=_StubPermission(allowed=False),
            users=users,
        )()

    assert user.settings.receive_vk_notifications is False
    assert users.saved == []


async def test_without_a_linked_vk_account_raises() -> None:
    user = _user()

    with pytest.raises(SocialAccountNotLinked):
        await _interactor(
            user, identity=None, permission=_StubPermission(allowed=True)
        )()


async def test_a_repeated_check_within_the_cooldown_is_refused() -> None:
    user = _user()
    permission = _StubPermission(allowed=True)

    with pytest.raises(NotificationsCheckTooFast):
        await _interactor(
            user,
            identity=_identity(user),
            permission=permission,
            cooldown=_Cooldown(active=True),
        )()

    assert permission.asked == []
