from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import override

import pytest

from fanfan.application.interactors.current_user.check_vk_messages_allowed import (
    CheckVkMessagesAllowed,
)
from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.ports.vk_messages import VkMessagesPermission
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.core.exceptions.users import SocialAccountNotLinked
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.vo.social_identity import SocialProvider, generate_social_identity_id
from fanfan.core.vo.user import UserId, generate_user_id

pytestmark = pytest.mark.asyncio

VK_USER_ID = 555


class _StubCurrentUser(CurrentUserProvider):
    def __init__(self, user_id: UserId) -> None:
        self._user_id = user_id

    @override
    async def require_user_id(self) -> UserId:
        return self._user_id


class _StubGateway(SocialIdentityGateway):
    def __init__(self, identity: SocialIdentity | None) -> None:
        self.identity = identity
        self.saved: list[SocialIdentity] = []

    @override
    async def get_by_provider(
        self, user_id: UserId, provider: SocialProvider
    ) -> SocialIdentity | None:
        return self.identity

    @override
    async def save(self, social_identity: SocialIdentity) -> None:
        self.saved.append(social_identity)


class _StubPermission(VkMessagesPermission):
    def __init__(self, *, allowed: bool) -> None:
        self.allowed = allowed
        self.asked: list[int] = []

    @override
    async def is_allowed(self, vk_user_id: int) -> bool:
        self.asked.append(vk_user_id)
        return self.allowed


class _StubUow(UnitOfWork):
    @override
    async def commit(self) -> None:
        pass


class _Cooldown(Cooldown):
    def __init__(self, *, active: bool = False) -> None:
        self.active = active

    @asynccontextmanager
    async def _claim(self) -> AsyncGenerator[None]:
        if self.active:
            raise CooldownActive(retry_after=1)
        yield

    @override
    def claim(self, key: str, seconds: int) -> AbstractAsyncContextManager[None]:
        return self._claim()


def _identity(user_id: UserId, *, allowed: bool | None = None) -> SocialIdentity:
    return SocialIdentity(
        id=generate_social_identity_id(),
        user_id=user_id,
        provider=SocialProvider.VK,
        subject=str(VK_USER_ID),
        provider_user_id=VK_USER_ID,
        messages_allowed=allowed,
    )


def _interactor(
    gateway: _StubGateway,
    permission: _StubPermission,
    user_id: UserId,
    cooldown: _Cooldown | None = None,
) -> CheckVkMessagesAllowed:
    return CheckVkMessagesAllowed(
        current_user_provider=_StubCurrentUser(user_id),
        social_identity_gateway=gateway,
        vk_messages_permission=permission,
        cooldown=cooldown or _Cooldown(),
        uow=_StubUow(),
    )


async def test_asks_vk_and_records_the_answer() -> None:
    user_id = generate_user_id()
    gateway = _StubGateway(_identity(user_id))
    permission = _StubPermission(allowed=True)

    result = await _interactor(gateway, permission, user_id)()

    assert result.messages_allowed is True
    assert permission.asked == [VK_USER_ID]
    assert gateway.saved[0].messages_allowed is True


async def test_an_unchanged_answer_is_not_saved() -> None:
    user_id = generate_user_id()
    gateway = _StubGateway(_identity(user_id, allowed=False))

    result = await _interactor(gateway, _StubPermission(allowed=False), user_id)()

    assert result.messages_allowed is False
    assert gateway.saved == []


async def test_within_the_cooldown_returns_the_stored_answer() -> None:
    user_id = generate_user_id()
    gateway = _StubGateway(_identity(user_id, allowed=False))
    permission = _StubPermission(allowed=True)

    result = await _interactor(gateway, permission, user_id, _Cooldown(active=True))()

    assert result.messages_allowed is False
    assert permission.asked == []


async def test_without_a_linked_vk_account_raises() -> None:
    user_id = generate_user_id()
    gateway = _StubGateway(None)

    with pytest.raises(SocialAccountNotLinked):
        await _interactor(gateway, _StubPermission(allowed=True), user_id)()
