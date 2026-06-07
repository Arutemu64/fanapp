from datetime import UTC, datetime

from pydantic import BaseModel, Field

from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.auth import InvalidOtpCode
from fanfan.core.exceptions.users import EmailAlreadyExists
from fanfan.core.services.email_login import (
    EMAIL_OTP_LOCKOUT_SECONDS,
    EMAIL_OTP_MAX_ATTEMPTS,
)
from fanfan.core.utils.email import normalize_email


class ConfirmEmailCodeInput(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ConfirmEmailCode:
    def __init__(
        self,
        user_repo: UserRepository,
        current_user_provider: CurrentUserProvider,
        token_registry: TokenRegistry,
        trx: TransactionManager,
    ):
        self.user_repo = user_repo
        self.current_user_provider = current_user_provider
        self.token_registry = token_registry
        self.trx = trx

    async def __call__(self, data: ConfirmEmailCodeInput) -> None:
        current_user = await self.current_user_provider.require_user()

        target_email = await self.token_registry.consume_email_confirmation_code(
            user_id=current_user.id,
            code=data.code,
            max_attempts=EMAIL_OTP_MAX_ATTEMPTS,
            window_seconds=EMAIL_OTP_LOCKOUT_SECONDS,
        )
        if target_email is None:
            raise InvalidOtpCode

        normalized_target_email = normalize_email(target_email)

        if current_user.pending_email == normalized_target_email:
            existing_user = await self.user_repo.get_by_email(normalized_target_email)
            if existing_user is not None and existing_user.id != current_user.id:
                raise InvalidOtpCode

            current_user.confirm_pending_email(datetime.now(UTC))
        elif current_user.email != normalized_target_email:
            raise InvalidOtpCode
        else:
            current_user.verify_email(datetime.now(UTC))
        try:
            await self.user_repo.save(current_user)
            await self.trx.commit()
        except EmailAlreadyExists as e:
            raise InvalidOtpCode from e
