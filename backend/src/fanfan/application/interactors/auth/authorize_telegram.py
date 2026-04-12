from pydantic import BaseModel

from fanfan.application.dto.token import Token
from fanfan.application.ports.repositories.social_ids import SocialIdentityRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.security import SecurityService
from fanfan.application.services.user import UserService
from fanfan.core.models.social_account import SocialIdentity
from fanfan.core.models.user import User
from fanfan.core.vo.user import UserRole


class AuthorizeTelegramInput(BaseModel):
    user_id: int
    name: str


class AuthorizeTelegram:
    def __init__(
        self,
        user_repo: UserRepository,
        social_id_repo: SocialIdentityRepository,
        security: SecurityService,
        trx: TransactionManager,
        user_service: UserService,
    ) -> None:
        self.social_id_repo = social_id_repo
        self.trx = trx
        self.security = security
        self.user_repo = user_repo
        self.user_service = user_service

    async def __call__(self, data: AuthorizeTelegramInput) -> Token:
        telegram_id = str(data.user_id)
        user = await self.user_repo.get_by_social_id(
            provider_name="telegram", provider_account_id=telegram_id
        )

        if user:
            return self.security.create_token(user_id=user.id)

        user = User(
            username=await self.user_service.generate_username(),
            role=UserRole.VISITOR,
            hashed_password=None,
            pending_email=None,
            email_verified_at=None,
        )
        await self.user_repo.add(user)
        await self.trx.flush()
        social_id = SocialIdentity(
            user_id=user.id,
            provider="telegram",
            provider_id=str(data.user_id),
        )
        await self.social_id_repo.add(social_id)
        await self.trx.commit()
        return self.security.create_token(user_id=user.id)
