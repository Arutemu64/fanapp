import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.user import UserService
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.models.user import User
from fanfan.core.vo.social_identity import SocialProvider, generate_social_identity_id
from fanfan.core.vo.user import UserRole, generate_user_id

logger = logging.getLogger(__name__)


class AuthorizeVkInput(BaseModel):
    subject: str
    provider_user_id: int


class AuthorizeVk:
    def __init__(
        self,
        user_gateway: UserGateway,
        social_identity_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        user_service: UserService,
        session_store: SessionStore,
    ) -> None:
        self.social_identity_gateway = social_identity_gateway
        self.uow = uow
        self.user_gateway = user_gateway
        self.user_service = user_service
        self.session_store = session_store

    async def __call__(self, data: AuthorizeVkInput) -> str:
        identity = await self.social_identity_gateway.get_by_subject(
            provider=SocialProvider.VK, subject=data.subject
        )

        if identity:
            return await self.session_store.create_session(identity.user_id)

        user = User.create(
            id=generate_user_id(),
            username=await self.user_service.generate_username(),
            role=UserRole.VISITOR,
            hashed_password=None,
        )
        await self.user_gateway.add(user)
        await self.uow.flush()
        await self.social_identity_gateway.add(
            SocialIdentity(
                id=generate_social_identity_id(),
                user_id=user.id,
                provider=SocialProvider.VK,
                subject=data.subject,
                provider_user_id=data.provider_user_id,
            )
        )
        await self.uow.commit()
        return await self.session_store.create_session(user.id)
