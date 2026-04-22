from datetime import UTC, datetime

from pydantic import BaseModel, Field

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.auth import InvalidOtpCode
from fanfan.core.exceptions.users import EmailAlreadyExists
from fanfan.core.utils.email import normalize_email


class ConfirmEmailCodeInput(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ConfirmEmailCode:
    def __init__(
        self,
        user_repo: UserRepository,
        id_provider: IdProvider,
        token_registry: TokenRegistry,
        trx: TransactionManager,
    ):
        self.user_repo = user_repo
        self.id_provider = id_provider
        self.token_registry = token_registry
        self.trx = trx

    async def __call__(self, data: ConfirmEmailCodeInput) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )

        target_email = await self.token_registry.consume_email_confirmation_code(
            user_id=current_user.id,
            code=data.code,
        )
        if target_email is None:
            raise InvalidOtpCode

        normalized_target_email = normalize_email(target_email)

        if current_user.pending_email == normalized_target_email:
            existing_user = await self.user_repo.get_by_email(normalized_target_email)
            if existing_user is not None and existing_user.id != current_user.id:
                raise InvalidOtpCode

            current_user.email = current_user.pending_email
            current_user.pending_email = None
        elif current_user.email != normalized_target_email:
            raise InvalidOtpCode

        current_user.email_verified_at = datetime.now(UTC)
        try:
            await self.user_repo.save(current_user)
            await self.trx.commit()
        except EmailAlreadyExists as e:
            raise InvalidOtpCode from e
