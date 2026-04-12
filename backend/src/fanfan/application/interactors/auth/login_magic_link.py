from datetime import UTC, datetime

from pydantic import BaseModel

from fanfan.application.dto.token import Token
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.security import SecurityService
from fanfan.core.exceptions.auth import InvalidToken
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.utils.email import normalize_email


class LoginMagicLinkInput(BaseModel):
    token: str


class LoginMagicLink:
    def __init__(
        self,
        user_repo: UserRepository,
        token_registry: TokenRegistry,
        security: SecurityService,
        trx: TransactionManager,
    ):
        self.user_repo = user_repo
        self.token_registry = token_registry
        self.security = security
        self.trx = trx

    async def __call__(self, data: LoginMagicLinkInput) -> Token:
        token_payload = await self.token_registry.consume_email_login_token(data.token)
        if token_payload is None:
            raise InvalidToken

        user_id, target_email = token_payload
        normalized_target_email = normalize_email(target_email)

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFound

        # A magic link proves mailbox ownership.
        # Once it is used, the account email can be treated as verified.
        if user.email is None or user.email != normalized_target_email:
            raise InvalidToken

        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)
            await self.user_repo.save(user)
            await self.trx.commit()

        return self.security.create_token(user_id=user.id)
