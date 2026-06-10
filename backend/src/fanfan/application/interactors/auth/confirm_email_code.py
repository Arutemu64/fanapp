from datetime import UTC, datetime

from pydantic import BaseModel, Field

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.auth import InvalidOtpCode
from fanfan.core.exceptions.users import EmailAlreadyExists
from fanfan.core.services.email_login import (
    EMAIL_OTP_LOCKOUT_SECONDS,
    EMAIL_OTP_MAX_ATTEMPTS,
)
from fanfan.core.vo.email import Email


class ConfirmEmailCodeInput(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ConfirmEmailCode:
    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        token_registry: TokenRegistry,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.token_registry = token_registry
        self.uow = uow

    async def __call__(self, data: ConfirmEmailCodeInput) -> None:
        current_user = await self.current_user_provider.require_user()

        target_email_value = await self.token_registry.consume_email_confirmation_code(
            user_id=current_user.id,
            code=data.code,
            max_attempts=EMAIL_OTP_MAX_ATTEMPTS,
            window_seconds=EMAIL_OTP_LOCKOUT_SECONDS,
        )
        if target_email_value is None:
            raise InvalidOtpCode

        target_email = Email(target_email_value)

        if current_user.pending_email == target_email:
            existing_user = await self.user_gateway.get_by_email(target_email.value)
            if existing_user is not None and existing_user.id != current_user.id:
                raise InvalidOtpCode

            current_user.confirm_pending_email(datetime.now(UTC))
        elif current_user.email != target_email:
            raise InvalidOtpCode
        else:
            current_user.verify_email(datetime.now(UTC))
        try:
            await self.user_gateway.save(current_user)
            await self.uow.commit()
        except EmailAlreadyExists as e:
            raise InvalidOtpCode from e
