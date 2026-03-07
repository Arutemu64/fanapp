from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.redis.auth_token_registry import RedisAuthTokenRegistry
from fanfan.core.exceptions.auth import InvalidToken
from fanfan.core.exceptions.users import UserNotFound


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
            user_id = await self.token_registry.consume_email_verification_token(
                token=data.token,
            )
            if user_id is None:
                raise InvalidToken

            user = await self.user_gateway.get_user_by_id(user_id)
            if user is None:
                raise UserNotFound

            user.is_verified = True
            await self.user_gateway.save_user(user)
            await self.uow.commit()
