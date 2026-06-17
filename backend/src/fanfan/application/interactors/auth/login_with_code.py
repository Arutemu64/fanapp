import logging

from pydantic import BaseModel, EmailStr, Field

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.auth import InvalidOtpCode
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.email_login import (
    EMAIL_OTP_LOCKOUT_SECONDS,
    EMAIL_OTP_MAX_ATTEMPTS,
)
from fanfan.core.vo.email import Email

logger = logging.getLogger(__name__)


class LoginWithCodeInput(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginWithCode:
    def __init__(
        self,
        user_gateway: UserGateway,
        token_registry: TokenRegistry,
        uow: UnitOfWork,
        session_store: SessionStore,
    ):
        self.user_gateway = user_gateway
        self.token_registry = token_registry
        self.uow = uow
        self.session_store = session_store

    async def __call__(self, data: LoginWithCodeInput) -> str:
        target_email = Email(data.email)
        user_id = await self.token_registry.consume_email_login_code(
            email=target_email.value,
            code=data.code,
            max_attempts=EMAIL_OTP_MAX_ATTEMPTS,
            window_seconds=EMAIL_OTP_LOCKOUT_SECONDS,
        )
        if user_id is None:
            logger.warning("Email code login failed", extra={"reason": "invalid_code"})
            raise InvalidOtpCode

        user = await self.user_gateway.get_by_id(user_id)
        if user is None:
            raise UserNotFound

        # The one-time email code proves mailbox ownership for this login.
        if user.email is None or user.email != target_email:
            logger.warning(
                "Email code login failed",
                extra={"reason": "email_mismatch", "actor_id": str(user.id)},
            )
            raise InvalidOtpCode

        logger.info(
            "User authenticated via email code",
            extra={"actor_id": str(user.id)},
        )
        return await self.session_store.create_session(user.id)
