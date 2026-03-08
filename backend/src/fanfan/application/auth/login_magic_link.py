from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.redis.auth_token_registry import RedisAuthTokenRegistry
from fanfan.core.dto.token import Token
from fanfan.core.exceptions.auth import InvalidToken
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.security import SecurityService


class LoginMagicLinkCommand(BaseModel):
    token: str


class LoginMagicLink:
    def __init__(
        self,
        user_gateway: UserGateway,
        token_registry: RedisAuthTokenRegistry,
        security: SecurityService,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.token_registry = token_registry
        self.security = security
        self.uow = uow

    async def __call__(self, data: LoginMagicLinkCommand) -> Token:
        async with self.uow:
            user_id = await self.token_registry.consume_email_login_token(data.token)
            if user_id is None:
                raise InvalidToken

            user = await self.user_gateway.get_user_by_id(user_id)
            if user is None:
                raise UserNotFound

            # A magic link proves mailbox ownership.
            # Once it is used, the account email can be treated as verified.
            if not user.is_verified:
                user.is_verified = True
                await self.user_gateway.save_user(user)
                await self.uow.commit()

            return self.security.create_token(user_id=user.id)
