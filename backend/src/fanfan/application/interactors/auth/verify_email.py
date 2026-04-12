from datetime import UTC, datetime

from pydantic import BaseModel

from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.auth import InvalidToken
from fanfan.core.exceptions.users import EmailAlreadyExists, UserNotFound
from fanfan.core.utils.email import normalize_email


class VerifyEmailInput(BaseModel):
    token: str


class VerifyEmail:
    def __init__(
        self,
        user_repo: UserRepository,
        token_registry: TokenRegistry,
        trx: TransactionManager,
    ):
        self.user_repo = user_repo
        self.token_registry = token_registry
        self.trx = trx

    async def __call__(self, data: VerifyEmailInput) -> None:
        token_payload = await self.token_registry.consume_email_verification_token(
            token=data.token,
        )
        if token_payload is None:
            raise InvalidToken

        user_id, target_email = token_payload
        normalized_target_email = normalize_email(target_email)

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFound

        if user.pending_email == normalized_target_email:
            existing_user = await self.user_repo.get_by_email(normalized_target_email)
            if existing_user is not None and existing_user.id != user.id:
                raise InvalidToken

            user.email = user.pending_email
            user.pending_email = None
        elif user.email == normalized_target_email:
            pass
        else:
            raise InvalidToken

        user.email_verified_at = datetime.now(UTC)
        try:
            await self.user_repo.save(user)
            await self.trx.commit()
        except EmailAlreadyExists as e:
            raise InvalidToken from e
