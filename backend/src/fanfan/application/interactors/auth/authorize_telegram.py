from pydantic import BaseModel

from fanfan.application.ports.repositories.social_ids import SocialIdentityRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.user import UserService
from fanfan.core.models.social_account import SocialIdentity
from fanfan.core.models.user import User
from fanfan.core.vo.social_identity import generate_social_identity_id
from fanfan.core.vo.user import UserRole, generate_user_id


class AuthorizeTelegramInput(BaseModel):
    user_id: int
    name: str


class AuthorizeTelegram:
    def __init__(
        self,
        user_repo: UserRepository,
        social_id_repo: SocialIdentityRepository,
        trx: TransactionManager,
        user_service: UserService,
        session_store: SessionStore,
    ) -> None:
        self.social_id_repo = social_id_repo
        self.trx = trx
        self.user_repo = user_repo
        self.user_service = user_service
        self.session_store = session_store

    async def __call__(self, data: AuthorizeTelegramInput) -> str:
        telegram_id = str(data.user_id)
        user = await self.user_repo.get_by_social_id(
            provider_name="telegram", provider_account_id=telegram_id
        )

        if user:
            return await self.session_store.create_session(user.id)

        user = User(
            id=generate_user_id(),
            username=await self.user_service.generate_username(),
            role=UserRole.VISITOR,
            hashed_password=None,
            pending_email=None,
            email_verified_at=None,
        )
        await self.user_repo.add(user)
        await self.trx.flush()
        social_id = SocialIdentity(
            id=generate_social_identity_id(),
            user_id=user.id,
            provider="telegram",
            provider_id=str(data.user_id),
        )
        await self.social_id_repo.add(social_id)
        await self.trx.commit()
        return await self.session_store.create_session(user.id)
