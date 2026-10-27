import logging
from typing import ClassVar

from pydantic import BaseModel, EmailStr, Field

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.application.ports.session_store import SessionStore
from fanfan.core.exceptions.auth import InvalidCredentials
from fanfan.core.exceptions.rate_limit import TooManyAttempts, TooManyLoginAttempts
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.fields import PASSWORD_MAX_LENGTH

logger = logging.getLogger(__name__)

LOGIN_EMAIL_MAX_ATTEMPTS = 5
LOGIN_IP_MAX_ATTEMPTS = 20
LOGIN_ATTEMPTS_WINDOW_SECONDS = 900


class AuthenticateUserInput(BaseModel):
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX_LENGTH, repr=False)
    client_ip: str | None = None


class AuthenticateUser:
    _dummy_hash: ClassVar[str | None] = None

    def __init__(
        self,
        user_gateway: UserGateway,
        password_hasher: PasswordHasher,
        session_store: SessionStore,
        rate_limiter: RateLimiter,
    ) -> None:
        self.user_gateway = user_gateway
        self.password_hasher = password_hasher
        self.session_store = session_store
        self.rate_limiter = rate_limiter

    async def _get_dummy_hash(self) -> str:
        if AuthenticateUser._dummy_hash is None:
            AuthenticateUser._dummy_hash = await self.password_hasher.hash(
                "dummy_password"
            )
        return AuthenticateUser._dummy_hash

    async def __call__(self, data: AuthenticateUserInput) -> str:
        normalized_email = normalize_email(data.email)

        await self._register_attempt(normalized_email, data.client_ip)

        user = await self.user_gateway.get_by_email(normalized_email)
        if user is None:
            await self.password_hasher.verify(
                data.password, await self._get_dummy_hash()
            )
            logger.warning(
                "Password login failed",
                extra={"reason": "user_not_found", "client_ip": data.client_ip},
            )
            raise InvalidCredentials
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
        if not await self.password_hasher.verify(data.password, user.hashed_password):
            logger.warning(
                "Password login failed",
                extra={
                    "reason": "invalid_password",
                    "actor_id": str(user.id),
                    "client_ip": data.client_ip,
                },
            )
            raise InvalidCredentials

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
