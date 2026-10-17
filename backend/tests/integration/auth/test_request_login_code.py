import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.request_login_code import (
    LOGIN_CODE_IP_MAX_REQUESTS,
    RequestLoginCode,
    RequestLoginCodeInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed
from fanfan.core.exceptions.rate_limit import (
    EmailCodeRequestTooFast,
    TooManyLoginCodeRequests,
)
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id
from tests.fakes.captcha import FakeCaptchaVerifier
from tests.fakes.email_sender import FakeEmailSender

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_request_login_code_provisions_new_user_and_sends_code(
    dishka_request: AsyncContainer,
) -> None:
    interactor = await dishka_request.get(RequestLoginCode)
    user_gateway = await dishka_request.get(UserGateway)
    email_sender = await dishka_request.get(FakeEmailSender)

    await interactor(RequestLoginCodeInput(email="new.user@example.com"))

    # An unknown email registers the account on the spot, so the same flow both
    # signs up and delivers the one-time code.
    user = await user_gateway.get_by_email("new.user@example.com")
    assert user is not None
    assert user.role is UserRole.VISITOR
    assert len(email_sender.sent_messages) == 1
    assert email_sender.sent_messages[0].recipients[0].email == "new.user@example.com"


async def test_request_login_code_reuses_existing_user(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(RequestLoginCode)
    user_gateway = await dishka_request.get(UserGateway)
    email_sender = await dishka_request.get(FakeEmailSender)

    existing = User(
        id=generate_user_id(),
        username=Username("existing"),
        email=Email("existing@example.com"),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(existing)
    await uow.commit()

    await interactor(RequestLoginCodeInput(email="Existing@Example.com"))

    # A known email must not create a second account; the code goes to the
    # existing user. Asserting the recipient is the normalized existing address
    # catches a case-handling regression that would provision a fresh account
    # for the raw "Existing@Example.com" spelling and mail the code there.
    reloaded = await user_gateway.get_by_email("existing@example.com")
    assert reloaded is not None
    assert reloaded.id == existing.id
    assert len(email_sender.sent_messages) == 1
    assert email_sender.sent_messages[0].recipients[0].email == "existing@example.com"


async def test_request_login_code_rejected_by_captcha_does_nothing(
    dishka_request: AsyncContainer,
) -> None:
    interactor = await dishka_request.get(RequestLoginCode)
    user_gateway = await dishka_request.get(UserGateway)
    email_sender = await dishka_request.get(FakeEmailSender)
    captcha = await dishka_request.get(FakeCaptchaVerifier)
    captcha.reject = True

    with pytest.raises(CaptchaVerificationFailed):
        await interactor(
            RequestLoginCodeInput(email="bot@example.com", captcha_token="bad")
        )

    # Bots are turned away before any account is provisioned or email sent.
    assert await user_gateway.get_by_email("bot@example.com") is None
    assert email_sender.sent_messages == []


async def test_request_login_code_second_request_hits_cooldown(
    dishka_request: AsyncContainer,
) -> None:
    interactor = await dishka_request.get(RequestLoginCode)
    email_sender = await dishka_request.get(FakeEmailSender)

    await interactor(RequestLoginCodeInput(email="cooldown@example.com"))
    # The per-email lock records its cooldown on the first clean exit, so an
    # immediate retry for the same email is rejected.
    with pytest.raises(EmailCodeRequestTooFast):
        await interactor(RequestLoginCodeInput(email="cooldown@example.com"))

    assert len(email_sender.sent_messages) == 1


async def test_request_login_code_caps_requests_per_ip(
    dishka_request: AsyncContainer,
) -> None:
    interactor = await dishka_request.get(RequestLoginCode)
    email_sender = await dishka_request.get(FakeEmailSender)
    captcha = await dishka_request.get(FakeCaptchaVerifier)

    # A distinct email each time, so only the per-IP cap can stop the spray.
    for i in range(LOGIN_CODE_IP_MAX_REQUESTS):
        await interactor(
            RequestLoginCodeInput(
                email=f"spray{i}@example.com", client_ip="203.0.113.7"
            )
        )

    with pytest.raises(TooManyLoginCodeRequests):
        await interactor(
            RequestLoginCodeInput(
                email="spray-over@example.com", client_ip="203.0.113.7"
            )
        )
    # Counted before the captcha, so a flood never reaches its PBKDF2 check.
    assert len(captcha.verified_tokens) == LOGIN_CODE_IP_MAX_REQUESTS
    assert len(email_sender.sent_messages) == LOGIN_CODE_IP_MAX_REQUESTS

    # Another address behind its own IP is unaffected.
    await interactor(
        RequestLoginCodeInput(email="neighbour@example.com", client_ip="203.0.113.8")
    )
