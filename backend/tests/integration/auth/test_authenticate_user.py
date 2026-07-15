import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.authenticate_user import (
    LOGIN_EMAIL_MAX_ATTEMPTS,
    AuthenticateUser,
    AuthenticateUserInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.auth import InvalidCredentials
from fanfan.core.exceptions.rate_limit import TooManyLoginAttempts
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

PASSWORD = "correct-horse-battery"
CLIENT_IP = "203.0.113.7"


async def _user_with_password(
    user_gateway: UserGateway,
    password_hasher: PasswordHasher,
    uow: UnitOfWork,
    email: str,
    password: str | None,
) -> User:
    user = User(
        id=generate_user_id(),
        username=Username("login_user"),
        email=Email(email),
        hashed_password=(password_hasher.hash(password) if password else None),
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()
    return user


async def test_authenticate_user_with_correct_password_creates_session(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AuthenticateUser)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)
    session_store = await dishka_request.get(SessionStore)

    user = await _user_with_password(
        user_gateway, password_hasher, uow, "login.user@example.com", PASSWORD
    )

    session_id = await interactor(
        AuthenticateUserInput(
            email="Login.User@Example.COM", password=PASSWORD, client_ip=CLIENT_IP
        )
    )

    resolution = await session_store.resolve_session(session_id)
    assert resolution.user_id == user.id


async def test_authenticate_user_with_wrong_password_raises_invalid_credentials(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AuthenticateUser)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    await _user_with_password(
        user_gateway, password_hasher, uow, "login.user@example.com", PASSWORD
    )

    with pytest.raises(InvalidCredentials):
        await interactor(
            AuthenticateUserInput(
                email="login.user@example.com", password="wrong-password"
            )
        )


async def test_authenticate_user_unknown_email_raises_invalid_credentials(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthenticateUser)

    with pytest.raises(InvalidCredentials):
        await interactor(
            AuthenticateUserInput(email="nobody@example.com", password=PASSWORD)
        )


async def test_authenticate_user_without_password_raises_invalid_credentials(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    # A social-only account has no password hash; a password login must fail
    # cleanly rather than crash on verification.
    interactor = await dishka_request.get(AuthenticateUser)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    await _user_with_password(
        user_gateway, password_hasher, uow, "social.only@example.com", None
    )

    with pytest.raises(InvalidCredentials):
        await interactor(
            AuthenticateUserInput(email="social.only@example.com", password=PASSWORD)
        )


async def test_authenticate_user_locks_out_after_too_many_attempts(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(AuthenticateUser)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    await _user_with_password(
        user_gateway, password_hasher, uow, "login.user@example.com", PASSWORD
    )

    # The per-email counter allows LOGIN_EMAIL_MAX_ATTEMPTS wrong tries; each is
    # a normal invalid-credentials failure.
    for _ in range(LOGIN_EMAIL_MAX_ATTEMPTS):
        with pytest.raises(InvalidCredentials):
            await interactor(
                AuthenticateUserInput(
                    email="login.user@example.com", password="wrong-password"
                )
            )

    # The next attempt is blocked before the password is even checked, so even
    # the correct password is rejected while locked out.
    with pytest.raises(TooManyLoginAttempts):
        await interactor(
            AuthenticateUserInput(email="login.user@example.com", password=PASSWORD)
        )


async def test_authenticate_user_success_resets_attempt_counter(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    # A few typos followed by a correct password must not leave the account near
    # lockout: a successful login clears the counters.
    interactor = await dishka_request.get(AuthenticateUser)
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)

    await _user_with_password(
        user_gateway, password_hasher, uow, "login.user@example.com", PASSWORD
    )

    for _ in range(LOGIN_EMAIL_MAX_ATTEMPTS - 1):
        with pytest.raises(InvalidCredentials):
            await interactor(
                AuthenticateUserInput(
                    email="login.user@example.com", password="wrong-password"
                )
            )

    # Correct password resets the counter...
    await interactor(
        AuthenticateUserInput(email="login.user@example.com", password=PASSWORD)
    )

    # ...so a fresh run of wrong attempts is again allowed without an early lockout.
    for _ in range(LOGIN_EMAIL_MAX_ATTEMPTS):
        with pytest.raises(InvalidCredentials):
            await interactor(
                AuthenticateUserInput(
                    email="login.user@example.com", password="wrong-password"
                )
            )
