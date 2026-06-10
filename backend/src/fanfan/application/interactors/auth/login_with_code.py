from datetime import UTC, datetime

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
from fanfan.core.utils.email import normalize_email


class LoginWithCodeInput(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginWithCode:
    def __init__(
        self,
        user_repo: UserGateway,
        token_registry: TokenRegistry,
        uow: UnitOfWork,
        session_store: SessionStore,
    ):
        self.user_repo = user_repo
        self.token_registry = token_registry
        self.uow = uow
        self.session_store = session_store

    async def __call__(self, data: LoginWithCodeInput) -> str:
        normalized_target_email = normalize_email(data.email)
        user_id = await self.token_registry.consume_email_login_code(
            email=normalized_target_email,
            code=data.code,
            max_attempts=EMAIL_OTP_MAX_ATTEMPTS,
            window_seconds=EMAIL_OTP_LOCKOUT_SECONDS,
        )
        if user_id is None:
            raise InvalidOtpCode

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFound

        # The one-time email code proves mailbox ownership for this login.
        if user.email is None or user.email != normalized_target_email:
            raise InvalidOtpCode

        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)
            await self.user_repo.save(user)
            await self.uow.commit()

        return await self.session_store.create_session(user.id)
