import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.register_user import (
    RegisterUser,
    RegisterUserInput,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.security import SecurityService
from fanfan.core.events.users import CreatedUserEvent
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.vo.user import Username, UserRole
from tests.fakes.event_broker import FakeEventBroker

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_register_user_creates_visitor_with_password_and_publishes_event(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(RegisterUser)
    user_repo = await dishka_request.get(UserRepository)
    security = await dishka_request.get(SecurityService)
    events_broker = await dishka_request.get(FakeEventBroker)

    await interactor(
        RegisterUserInput(email="New.Visitor@Example.COM", password="strong-password")
    )

    saved_user = await user_repo.get_by_email("new.visitor@example.com")
    assert saved_user is not None
    assert saved_user.email == "new.visitor@example.com"
    assert saved_user.username is not None
    assert saved_user.role == UserRole.VISITOR
    assert saved_user.pending_email is None
    assert saved_user.email_verified_at is None
    assert saved_user.hashed_password is not None
    assert saved_user.hashed_password != "strong-password"
    assert security.verify_password("strong-password", saved_user.hashed_password)
    assert events_broker.published_events == [CreatedUserEvent(user_id=saved_user.id)]


async def test_register_user_raises_when_email_already_exists(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(RegisterUser)
    user_repo = await dishka_request.get(UserRepository)
    trx = await dishka_request.get(TransactionManager)
    events_broker = await dishka_request.get(FakeEventBroker)

    existing_user = User(
        username=Username("existing_user"),
        email="existing@example.com",
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_repo.add(existing_user)
    await trx.commit()

    with pytest.raises(UserAlreadyExists):
        await interactor(
            RegisterUserInput(email="Existing@Example.COM", password="strong-password")
        )

    assert (await user_repo.get_by_email("existing@example.com")) == existing_user
    assert events_broker.published_events == []


async def test_register_user_raises_when_email_is_pending_on_another_user(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(RegisterUser)
    user_repo = await dishka_request.get(UserRepository)
    trx = await dishka_request.get(TransactionManager)
    events_broker = await dishka_request.get(FakeEventBroker)

    existing_user = User(
        username=Username("pending_email_user"),
        email="current@example.com",
        pending_email="reserved@example.com",
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_repo.add(existing_user)
    await trx.commit()

    with pytest.raises(UserAlreadyExists):
        await interactor(
            RegisterUserInput(email="Reserved@Example.COM", password="strong-password")
        )

    assert (
        await user_repo.get_by_pending_email("reserved@example.com")
    ) == existing_user
    assert events_broker.published_events == []
