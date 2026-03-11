from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.dto.token import Token
from fanfan.core.models.social_account import SocialAccount
from fanfan.core.models.user import User
from fanfan.core.services.security import SecurityService
from fanfan.core.services.user import UserService
from fanfan.core.vo.user import UserRole


class AuthorizeTelegramCommand(BaseModel):
    user_id: int
    name: str


class AuthorizeTelegram:
    def __init__(
        self,
        user_gateway: UserGateway,
        security: SecurityService,
        uow: UnitOfWork,
        user_service: UserService,
    ) -> None:
        self.uow = uow
        self.security = security
        self.user_gateway = user_gateway
        self.user_service = user_service

    async def __call__(self, data: AuthorizeTelegramCommand) -> Token:
        user = await self.user_gateway.get_user_by_social_id(
            provider_name="telegram",
            provider_account_id=str(data.user_id),
        )

        if user:
            return self.security.create_token(user_id=user.id)

        async with self.uow:
            user = User(
                username=await self.user_service.generate_username(),
                role=UserRole.VISITOR,
                hashed_password=None,
                is_verified=False,
            )
            await self.user_gateway.add_user(user)
            await self.uow.flush()
            social_id = SocialAccount(
                user_id=user.id,
                provider="telegram",
                provider_id=str(data.user_id),
            )
            await self.user_gateway.add_user_social_id(social_id)
            await self.uow.commit()
            return self.security.create_token(user_id=user.id)
