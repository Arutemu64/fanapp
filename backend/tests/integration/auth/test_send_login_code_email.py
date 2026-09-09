import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.send_login_code_email import (
    SendLoginCodeEmail,
    SendLoginCodeEmailInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.models.user import User
from fanfan.core.vo.user import Username, UserRole, generate_user_id
from tests.fakes.email_sender import FakeEmailSender

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_send_login_code_email_unknown_user_raises(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(SendLoginCodeEmail)
    email_sender = await dishka_request.get(FakeEmailSender)

    with pytest.raises(UserNotFound):
        await interactor(SendLoginCodeEmailInput(user_id=generate_user_id()))

    assert email_sender.sent_messages == []


async def test_send_login_code_email_user_without_email_raises(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SendLoginCodeEmail)
    user_gateway = await dishka_request.get(UserGateway)
    email_sender = await dishka_request.get(FakeEmailSender)

    # A Telegram-only account has no email, so there is nowhere to send the code.
    user = User(
        id=generate_user_id(),
        username=Username("no_email"),
        email=None,
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()

    with pytest.raises(UserHasNoEmail):
        await interactor(SendLoginCodeEmailInput(user_id=user.id))

    assert email_sender.sent_messages == []
