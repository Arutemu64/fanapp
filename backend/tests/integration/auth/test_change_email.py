from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.change_email import (
    ChangeEmail,
    ChangeEmailInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.users import EmailConfirmationCodeRequested
from fanfan.core.exceptions.rate_limit import EmailCodeRequestTooFast
from fanfan.core.exceptions.users import EmailAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id
from tests.fakes.event_broker import FakeEventBroker

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _user(
    user_gateway: UserGateway,
    uow: UnitOfWork,
    email: str,
    *,
    username: str = "email_user",
) -> User:
    user = User(
        id=generate_user_id(),
        username=Username(username),
        email=Email(email),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()
    return user


async def test_change_email_publishes_confirmation_request(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    # Changing an email does not update the account directly — it asks the email
    # subsystem to send a confirmation code to the new address.
    interactor = await dishka_request.get(ChangeEmail)
    user_gateway = await dishka_request.get(UserGateway)
    event_broker = await dishka_request.get(FakeEventBroker)

    user = await _user(user_gateway, uow, "old.address@example.com")
    login(user)

    await interactor(ChangeEmailInput(new_email="New.Address@Example.COM"))

    assert event_broker.published_events == [
        EmailConfirmationCodeRequested(
            user_id=user.id, target_email="new.address@example.com"
        )
    ]

    # The stored email stays put until the code is confirmed.
    saved_user = await user_gateway.get_by_id(user.id)
    assert saved_user is not None
    assert saved_user.email == Email("old.address@example.com")


async def test_change_email_to_same_address_is_noop(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ChangeEmail)
    user_gateway = await dishka_request.get(UserGateway)
    event_broker = await dishka_request.get(FakeEventBroker)

    user = await _user(user_gateway, uow, "same.address@example.com")
    login(user)

    # Normalization means differing case is still the same address.
    await interactor(ChangeEmailInput(new_email="Same.Address@Example.COM"))

    assert event_broker.published_events == []


async def test_change_email_to_address_taken_by_another_user_raises(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ChangeEmail)
    user_gateway = await dishka_request.get(UserGateway)
    event_broker = await dishka_request.get(FakeEventBroker)

    await _user(user_gateway, uow, "taken@example.com", username="other_owner")
    user = await _user(user_gateway, uow, "mine@example.com", username="email_user")
    login(user)

    with pytest.raises(EmailAlreadyExists):
        await interactor(ChangeEmailInput(new_email="taken@example.com"))

    assert event_broker.published_events == []


async def test_change_email_twice_in_a_row_hits_cooldown(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    # The per-address cooldown lock stops a second confirmation code being sent
    # to the same target immediately after the first.
    interactor = await dishka_request.get(ChangeEmail)
    user_gateway = await dishka_request.get(UserGateway)
    event_broker = await dishka_request.get(FakeEventBroker)

    user = await _user(user_gateway, uow, "old.address@example.com")
    login(user)

    await interactor(ChangeEmailInput(new_email="target@example.com"))
    with pytest.raises(EmailCodeRequestTooFast):
        await interactor(ChangeEmailInput(new_email="target@example.com"))

    # Only the first request produced an event.
    assert event_broker.published_events == [
        EmailConfirmationCodeRequested(
            user_id=user.id, target_email="target@example.com"
        )
    ]
