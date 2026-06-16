import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.register_user import (
    RegisterUser,
    RegisterUserInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_register_user_creates_visitor_with_hashed_password(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(RegisterUser)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    await interactor(
        RegisterUserInput(email="New.Visitor@Example.COM", password="strong-password")
    )

    saved_user = await user_gateway.get_by_email("new.visitor@example.com")
    assert saved_user is not None
    assert saved_user.email == Email("new.visitor@example.com")
    assert saved_user.username is not None
    assert saved_user.role == UserRole.VISITOR
    assert saved_user.hashed_password is not None
    assert saved_user.hashed_password != "strong-password"
    assert password_hasher.verify("strong-password", saved_user.hashed_password)


async def test_register_user_with_existing_email_is_silent_noop(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    # Registering an already-used email must NOT raise (avoids account
    # enumeration) and must NOT touch the existing account (avoids takeover).
    interactor = await dishka_request.get(RegisterUser)
    user_gateway = await dishka_request.get(UserGateway)

    existing_user = User(
        id=generate_user_id(),
        username=Username("existing_user"),
        email=Email("existing@example.com"),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(existing_user)
    await uow.commit()

    await interactor(
        RegisterUserInput(email="Existing@Example.COM", password="strong-password")
    )

    saved_user = await user_gateway.get_by_email("existing@example.com")
    assert saved_user is not None
    assert saved_user.id == existing_user.id
    # Password was never set on the existing account, so it must stay empty.
    assert saved_user.hashed_password is None
