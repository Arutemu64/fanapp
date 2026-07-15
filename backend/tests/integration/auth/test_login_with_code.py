import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.login_with_code import (
    LoginWithCode,
    LoginWithCodeInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.auth import InvalidOtpCode
from fanfan.core.exceptions.rate_limit import TooManyOtpAttempts
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.user import User
from fanfan.core.services.email_login import (
    EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    EMAIL_OTP_MAX_ATTEMPTS,
)
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

VALID_CODE = "123456"
WRONG_CODE = "000000"


async def _user_with_email(
    user_gateway: UserGateway,
    uow: UnitOfWork,
    email: str,
) -> User:
    user = User(
        id=generate_user_id(),
        username=Username("code_user"),
        email=Email(email),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()
    return user


async def test_login_with_code_creates_session_for_matching_email(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(LoginWithCode)
    user_gateway = await dishka_request.get(UserGateway)
    token_registry = await dishka_request.get(TokenRegistry)
    session_store = await dishka_request.get(SessionStore)

    user = await _user_with_email(user_gateway, uow, "code.user@example.com")
    await token_registry.issue_email_login_code(
        user_id=user.id,
        email=user.email.value,
        code=VALID_CODE,
        ttl_seconds=EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    )

    session_id = await interactor(
        LoginWithCodeInput(email="Code.User@Example.COM", code=VALID_CODE)
    )

    resolution = await session_store.resolve_session(session_id)
    assert resolution.user_id == user.id


async def test_login_with_code_wrong_code_raises_invalid_otp(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(LoginWithCode)
    user_gateway = await dishka_request.get(UserGateway)
    token_registry = await dishka_request.get(TokenRegistry)

    user = await _user_with_email(user_gateway, uow, "code.user@example.com")
    await token_registry.issue_email_login_code(
        user_id=user.id,
        email=user.email.value,
        code=VALID_CODE,
        ttl_seconds=EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    )

    with pytest.raises(InvalidOtpCode):
        await interactor(
            LoginWithCodeInput(email="code.user@example.com", code=WRONG_CODE)
        )


async def test_login_with_code_email_mismatch_raises_invalid_otp(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    # The code is keyed by the target email but stores the user id. If that user's
    # own email no longer matches the target, the code must not authenticate them
    # (defends against a stale/hijacked code proving ownership of a mailbox).
    interactor = await dishka_request.get(LoginWithCode)
    user_gateway = await dishka_request.get(UserGateway)
    token_registry = await dishka_request.get(TokenRegistry)

    user = await _user_with_email(user_gateway, uow, "real.owner@example.com")
    target_email = "someone.else@example.com"
    await token_registry.issue_email_login_code(
        user_id=user.id,
        email=target_email,
        code=VALID_CODE,
        ttl_seconds=EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    )

    with pytest.raises(InvalidOtpCode):
        await interactor(LoginWithCodeInput(email=target_email, code=VALID_CODE))


async def test_login_with_code_unknown_user_raises_user_not_found(
    dishka_request: AsyncContainer,
):
    # A code that resolves to a user id with no matching account.
    interactor = await dishka_request.get(LoginWithCode)
    token_registry = await dishka_request.get(TokenRegistry)

    orphan_email = "ghost@example.com"
    await token_registry.issue_email_login_code(
        user_id=generate_user_id(),
        email=orphan_email,
        code=VALID_CODE,
        ttl_seconds=EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    )

    with pytest.raises(UserNotFound):
        await interactor(LoginWithCodeInput(email=orphan_email, code=VALID_CODE))


async def test_login_with_code_locks_out_after_too_many_wrong_codes(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(LoginWithCode)
    user_gateway = await dishka_request.get(UserGateway)
    token_registry = await dishka_request.get(TokenRegistry)

    user = await _user_with_email(user_gateway, uow, "code.user@example.com")
    await token_registry.issue_email_login_code(
        user_id=user.id,
        email=user.email.value,
        code=VALID_CODE,
        ttl_seconds=EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    )

    # Exhaust the allowed wrong guesses; each is reported as an invalid code.
    for _ in range(EMAIL_OTP_MAX_ATTEMPTS):
        with pytest.raises(InvalidOtpCode):
            await interactor(
                LoginWithCodeInput(email=user.email.value, code=WRONG_CODE)
            )

    # The next attempt — even with the correct code — is locked out.
    with pytest.raises(TooManyOtpAttempts):
        await interactor(LoginWithCodeInput(email=user.email.value, code=VALID_CODE))
