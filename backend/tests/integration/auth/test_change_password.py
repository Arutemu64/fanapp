from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.change_password import (
    ChangePassword,
    ChangePasswordInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.auth import IncorrectPassword
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

OLD_PASSWORD = "old-password-123"
NEW_PASSWORD = "brand-new-password-456"


async def _user(
    user_gateway: UserGateway,
    password_hasher: PasswordHasher,
    uow: UnitOfWork,
    password: str | None,
) -> User:
    user = User(
        id=generate_user_id(),
        username=Username("pwd_user"),
        email=Email("pwd.user@example.com"),
        hashed_password=(password_hasher.hash(password) if password else None),
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()
    return user


async def test_change_password_with_correct_old_password_updates_hash(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ChangePassword)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)
    session_store = await dishka_request.get(SessionStore)

    user = await _user(user_gateway, password_hasher, uow, OLD_PASSWORD)
    login(user)

    session_id = await interactor(
        ChangePasswordInput(old_password=OLD_PASSWORD, new_password=NEW_PASSWORD)
    )

    saved_user = await user_gateway.get_by_id(user.id)
    assert saved_user is not None
    assert saved_user.hashed_password is not None
    assert password_hasher.verify(NEW_PASSWORD, saved_user.hashed_password)
    assert not password_hasher.verify(OLD_PASSWORD, saved_user.hashed_password)

    # The interactor returns a fresh, valid session.
    resolution = await session_store.resolve_session(session_id)
    assert resolution.user_id == user.id


async def test_change_password_with_wrong_old_password_raises(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ChangePassword)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    user = await _user(user_gateway, password_hasher, uow, OLD_PASSWORD)
    login(user)

    with pytest.raises(IncorrectPassword):
        await interactor(
            ChangePasswordInput(
                old_password="not-the-old-one", new_password=NEW_PASSWORD
            )
        )

    # Password must be unchanged after a rejected attempt.
    await uow.rollback()
    saved_user = await user_gateway.get_by_id(user.id)
    assert saved_user is not None
    assert password_hasher.verify(OLD_PASSWORD, saved_user.hashed_password)


async def test_change_password_without_old_password_when_one_is_set_raises(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    # Omitting the current password is only allowed for accounts that have none;
    # when a password exists it must be provided.
    interactor = await dishka_request.get(ChangePassword)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    user = await _user(user_gateway, password_hasher, uow, OLD_PASSWORD)
    login(user)

    with pytest.raises(IncorrectPassword):
        await interactor(
            ChangePasswordInput(old_password=None, new_password=NEW_PASSWORD)
        )


async def test_change_password_for_account_without_password_sets_one(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    # A social-only account (no password) can set an initial password without
    # supplying an old one.
    interactor = await dishka_request.get(ChangePassword)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    user = await _user(user_gateway, password_hasher, uow, None)
    login(user)

    await interactor(ChangePasswordInput(old_password=None, new_password=NEW_PASSWORD))

    saved_user = await user_gateway.get_by_id(user.id)
    assert saved_user is not None
    assert saved_user.hashed_password is not None
    assert password_hasher.verify(NEW_PASSWORD, saved_user.hashed_password)


async def test_change_password_revokes_existing_sessions(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ChangePassword)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)
    session_store = await dishka_request.get(SessionStore)

    user = await _user(user_gateway, password_hasher, uow, OLD_PASSWORD)
    login(user)

    # An already-open session that must be invalidated by the password change.
    old_session_id = await session_store.create_session(user.id)
    assert (await session_store.resolve_session(old_session_id)).user_id == user.id

    new_session_id = await interactor(
        ChangePasswordInput(old_password=OLD_PASSWORD, new_password=NEW_PASSWORD)
    )

    # The pre-existing session is gone; only the freshly issued one is valid.
    assert (await session_store.resolve_session(old_session_id)).user_id is None
    assert (await session_store.resolve_session(new_session_id)).user_id == user.id
