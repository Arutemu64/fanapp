from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import override

import pytest

from fanfan.application.interactors.current_user.enable_telegram_notifications import (
    EnableTelegramNotifications,
)
from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.notifier import TelegramNotifierPort
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.notifications import (
    NotificationsCheckTooFast,
    TelegramBotBlocked,
    UserRevokedChannel,
)
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.core.exceptions.users import SocialAccountNotLinked
from fanfan.core.models.notification import Notification
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.social_identity import SocialProvider, generate_social_identity_id
from fanfan.core.vo.user import UserId, Username, UserRole, generate_user_id

pytestmark = pytest.mark.asyncio


class _StubCurrentUser(CurrentUserProvider):
    def __init__(self, user: User) -> None:
        self._user = user

    @override
    async def require_user_id(self) -> UserId:
        return self._user.id


class _StubIdentities(SocialIdentityGateway):
    def __init__(self, identity: SocialIdentity | None) -> None:
        self._identity = identity

    @override
    async def get_by_provider(
        self, user_id: object, provider: SocialProvider
    ) -> SocialIdentity | None:
        return self._identity


class _StubUsers(UserGateway):
    """Hands out the stored user, re-read after the messenger check."""

    def __init__(self, user: User) -> None:
        self._user = user
        self.saved: list[User] = []

    @override
    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._user

    @override
    async def save(self, user: User) -> None:
        self.saved.append(user)


class _StubNotifier(TelegramNotifierPort):
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.sent: list[Notification] = []

    @override
    async def send_notification(self, notification: Notification) -> None:
        if self._error is not None:
            raise self._error
        self.sent.append(notification)


class _StubUow(UnitOfWork):
    @override
    async def commit(self) -> None:
        pass


class _Cooldown(Cooldown):
    """Gives the claim back when the block raises, like PostgresCooldown."""

    def __init__(self, *, active: bool = False) -> None:
        self._active = active
        self.released = False

    @asynccontextmanager
    async def _claim(self) -> AsyncGenerator[None]:
        if self._active:
            raise CooldownActive(retry_after=3)
        try:
            yield
        except BaseException:
            self.released = True
            raise

    @override
    def claim(self, key: str, seconds: int) -> AbstractAsyncContextManager[None]:
        return self._claim()


def _user() -> User:
    return User(
        id=generate_user_id(),
        username=Username("tester"),
        hashed_password=None,
        role=UserRole.VISITOR,
        settings=UserSettings(receive_telegram_notifications=False),
    )


def _identity(user: User) -> SocialIdentity:
    return SocialIdentity(
        id=generate_social_identity_id(),
        user_id=user.id,
        provider=SocialProvider.TELEGRAM,
        subject="sub",
        provider_user_id=42,
    )


def _interactor(
    user: User,
    *,
    identity: SocialIdentity | None,
    notifier: _StubNotifier,
    users: _StubUsers | None = None,
    cooldown: _Cooldown | None = None,
) -> EnableTelegramNotifications:
    return EnableTelegramNotifications(
        current_user_provider=_StubCurrentUser(user),
        social_identity_gateway=_StubIdentities(identity),
        user_gateway=users or _StubUsers(user),
        tg_notifier=notifier,
        cooldown=cooldown or _Cooldown(),
        uow=_StubUow(),
    )


async def test_a_delivered_confirmation_turns_telegram_on() -> None:
    user = _user()
    users = _StubUsers(user)
    notifier = _StubNotifier()

    await _interactor(user, identity=_identity(user), notifier=notifier, users=users)()

    assert [n.user_id for n in notifier.sent] == [user.id]
    assert user.settings.receive_telegram_notifications is True
    assert users.saved == [user]


async def test_a_blocked_bot_keeps_telegram_off() -> None:
    user = _user()
    users = _StubUsers(user)

    with pytest.raises(TelegramBotBlocked):
        await _interactor(
            user,
            identity=_identity(user),
            notifier=_StubNotifier(UserRevokedChannel()),
            users=users,
        )()

    assert user.settings.receive_telegram_notifications is False
    assert users.saved == []


async def test_without_a_linked_telegram_account_raises() -> None:
    user = _user()

    with pytest.raises(SocialAccountNotLinked):
        await _interactor(user, identity=None, notifier=_StubNotifier())()


async def test_a_repeated_check_within_the_cooldown_is_refused() -> None:
    user = _user()
    notifier = _StubNotifier()

    with pytest.raises(NotificationsCheckTooFast):
        await _interactor(
            user,
            identity=_identity(user),
            notifier=notifier,
            cooldown=_Cooldown(active=True),
        )()

    assert notifier.sent == []


async def test_a_refused_check_keeps_its_cooldown() -> None:
    user = _user()
    cooldown = _Cooldown()

    with pytest.raises(TelegramBotBlocked):
        await _interactor(
            user,
            identity=_identity(user),
            notifier=_StubNotifier(UserRevokedChannel()),
            cooldown=cooldown,
        )()

    assert cooldown.released is False
