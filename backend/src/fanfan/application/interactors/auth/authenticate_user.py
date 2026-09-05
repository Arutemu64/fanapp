import logging
from typing import ClassVar

from pydantic import BaseModel, EmailStr

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.application.ports.session_store import SessionStore
from fanfan.core.exceptions.auth import InvalidCredentials
from fanfan.core.exceptions.rate_limit import TooManyAttempts, TooManyLoginAttempts
from fanfan.core.utils.email import normalize_email

logger = logging.getLogger(__name__)

# Per-email limit stops a targeted brute-force of one account's password.
LOGIN_EMAIL_MAX_ATTEMPTS = 5
# Per-IP limit stops credential stuffing (many emails from one source). Higher
# than the email limit so a shared NAT/office IP is not locked out too easily.
LOGIN_IP_MAX_ATTEMPTS = 20
# Window and lockout duration shared by both counters.
LOGIN_ATTEMPTS_WINDOW_SECONDS = 900


class AuthenticateUserInput(BaseModel):
    email: EmailStr
    password: str
    # Caller (web route) fills this in; the interactor stays framework-agnostic.
    client_ip: str | None = None


class AuthenticateUser:
    # Argon2 is deliberately slow; the dummy hash used to equalise timing on the
    # user-not-found branch only needs computing once per process, not per
    # request. Cached on the class, filled lazily from the injected hasher so the
    # application layer stays free of the concrete crypto library.
    _dummy_hash: ClassVar[str | None] = None

    def __init__(
        self,
        user_gateway: UserGateway,
        password_hasher: PasswordHasher,
        session_store: SessionStore,
        rate_limiter: RateLimiter,
    ):
        self.user_gateway = user_gateway
        self.password_hasher = password_hasher
        self.session_store = session_store
        self.rate_limiter = rate_limiter
        if AuthenticateUser._dummy_hash is None:
            AuthenticateUser._dummy_hash = self.password_hasher.hash("dummy_password")
        self.dummy_hash = AuthenticateUser._dummy_hash

    async def __call__(self, data: AuthenticateUserInput) -> str:
        normalized_email = normalize_email(data.email)

        # Count this attempt before doing any work. Counting unknown emails too
        # keeps the timing identical and stops attackers from probing for free.
        await self._register_attempt(normalized_email, data.client_ip)

        user = await self.user_gateway.get_by_email(normalized_email)
        if user is None:
            # Hash against a dummy value so a nonexistent user takes the same
            # time as a wrong password, and the response can't be timed to
            # enumerate accounts.
            self.password_hasher.verify(data.password, self.dummy_hash)
            # Email is omitted from the log on purpose to avoid storing PII;
            # client_ip is kept so repeated failures can be correlated.
            logger.warning(
                "Password login failed",
                extra={"reason": "user_not_found", "client_ip": data.client_ip},
            )
            raise InvalidCredentials
        # Social-only accounts may have no password yet.
        # Return a normal auth failure instead of crashing on password verification.
        if user.hashed_password is None:
            logger.warning(
                "Password login failed",
                extra={
                    "reason": "no_password_set",
                    "actor_id": str(user.id),
                    "client_ip": data.client_ip,
                },
            )
            raise InvalidCredentials
        if not self.password_hasher.verify(data.password, user.hashed_password):
            logger.warning(
                "Password login failed",
                extra={
                    "reason": "invalid_password",
                    "actor_id": str(user.id),
                    "client_ip": data.client_ip,
                },
            )
            raise InvalidCredentials

        # Successful login: clear the counters so a legitimate user is never
        # locked out by their own earlier typos.
        await self._reset_attempts(normalized_email, data.client_ip)
        logger.info(
            "User authenticated via password",
            extra={"actor_id": str(user.id), "client_ip": data.client_ip},
        )
        return await self.session_store.create_session(user.id)

    async def _register_attempt(self, email: str, client_ip: str | None) -> None:
        try:
            await self.rate_limiter.hit(
                f"login:email:{email}",
                limit=LOGIN_EMAIL_MAX_ATTEMPTS,
                window_seconds=LOGIN_ATTEMPTS_WINDOW_SECONDS,
            )
            if client_ip:
                await self.rate_limiter.hit(
                    f"login:ip:{client_ip}",
                    limit=LOGIN_IP_MAX_ATTEMPTS,
                    window_seconds=LOGIN_ATTEMPTS_WINDOW_SECONDS,
                )
        except TooManyAttempts as e:
            logger.warning(
                "Login blocked: too many attempts",
                extra={"client_ip": client_ip},
            )
            raise TooManyLoginAttempts(retry_after=e.details["retry_after"]) from e

    async def _reset_attempts(self, email: str, client_ip: str | None) -> None:
        await self.rate_limiter.reset(f"login:email:{email}")
        if client_ip:
            await self.rate_limiter.reset(f"login:ip:{client_ip}")
