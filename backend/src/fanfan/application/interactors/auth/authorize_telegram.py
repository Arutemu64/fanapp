from pydantic import BaseModel

from fanfan.application.ports.gateways.social_ids import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.uow import UnitOfWork
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
        user_gateway: UserGateway,
        social_id_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        user_service: UserService,
        session_store: SessionStore,
    ) -> None:
        self.social_id_gateway = social_id_gateway
        self.uow = uow
        self.user_gateway = user_gateway
        self.user_service = user_service
        self.session_store = session_store

    async def __call__(self, data: AuthorizeTelegramInput) -> str:
        telegram_id = str(data.user_id)
        user = await self.user_gateway.get_by_social_id(
            provider_name="telegram", provider_account_id=telegram_id
        )

        if user:
            return await self.session_store.create_session(user.id)

        user = User.create(
            id=generate_user_id(),
            username=await self.user_service.generate_username(),
            role=UserRole.VISITOR,
            hashed_password=None,
        )
        await self.user_gateway.add(user)
        await self.uow.flush()
        social_id = SocialIdentity(
            id=generate_social_identity_id(),
            user_id=user.id,
            provider="telegram",
            provider_id=str(data.user_id),
        )
        await self.social_id_gateway.add(social_id)
        await self.uow.commit()
        return await self.session_store.create_session(user.id)
