from pydantic import BaseModel, EmailStr

from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.services.security import SecurityService
from fanfan.core.exceptions.auth import InvalidCredentials
from fanfan.core.exceptions.rate_limit import TooManyAttempts, TooManyLoginAttempts
from fanfan.core.utils.email import normalize_email

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
    def __init__(
        self,
        user_repo: UserRepository,
        security: SecurityService,
        session_store: SessionStore,
        rate_limiter: RateLimiter,
    ):
        self.user_repo = user_repo
        self.security = security
        self.session_store = session_store
        self.rate_limiter = rate_limiter
        self.dummy_hash = self.security.hash_password("dummy_password")

    async def __call__(self, data: AuthenticateUserInput) -> str:
        normalized_email = normalize_email(data.email)

        # Count this attempt before doing any work. Counting unknown emails too
        # keeps the timing identical and stops attackers from probing for free.
        await self._register_attempt(normalized_email, data.client_ip)

        user = await self.user_repo.get_by_email(normalized_email)
        if user is None:
            # Prevent timing attack
            self.security.verify_password(data.password, self.dummy_hash)
            raise InvalidCredentials
        # Social-only accounts may have no password yet.
        # Return a normal auth failure instead of crashing on password verification.
        if user.hashed_password is None:
            raise InvalidCredentials
        if not self.security.verify_password(data.password, user.hashed_password):
            raise InvalidCredentials

        # Successful login: clear the counters so a legitimate user is never
        # locked out by their own earlier typos.
        await self._reset_attempts(normalized_email, data.client_ip)
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
            raise TooManyLoginAttempts(retry_after=e.details["retry_after"]) from e

    async def _reset_attempts(self, email: str, client_ip: str | None) -> None:
        await self.rate_limiter.reset(f"login:email:{email}")
        if client_ip:
            await self.rate_limiter.reset(f"login:ip:{client_ip}")
