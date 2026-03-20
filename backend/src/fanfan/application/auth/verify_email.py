from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.redis.auth_token_registry import RedisAuthTokenRegistry
from fanfan.application.common.constraints import get_constraint_name
from fanfan.core.exceptions.auth import InvalidToken
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.utils.email import normalize_email


class VerifyEmailCommand(BaseModel):
    token: str


class VerifyEmail:
    def __init__(
        self,
        user_gateway: UserGateway,
        token_registry: RedisAuthTokenRegistry,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.token_registry = token_registry
        self.uow = uow

    async def __call__(self, data: VerifyEmailCommand) -> None:
        async with self.uow:
            token_payload = await self.token_registry.consume_email_verification_token(
                token=data.token,
            )
            if token_payload is None:
                raise InvalidToken

            user_id, target_email = token_payload
            normalized_target_email = normalize_email(target_email)

            user = await self.user_gateway.get_user_by_id(user_id)
            if user is None:
                raise UserNotFound

            if user.pending_email == normalized_target_email:
                existing_user = await self.user_gateway.get_user_by_email(
                    normalized_target_email
                )
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
                await self.user_gateway.save_user(user)
                await self.uow.commit()
            except IntegrityError as e:
                if get_constraint_name(e) in {
                    "ix_users_email",
                    "ix_users_pending_email",
                }:
                    raise InvalidToken from e
                raise
