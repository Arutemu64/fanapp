import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import (
    TelegramAlreadyLinkedToAnotherUser,
    UserAlreadyHasTelegramLinked,
)
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.vo.social_identity import generate_social_identity_id

logger = logging.getLogger(__name__)


class LinkTelegramAccountInput(BaseModel):
    user_id: int


class LinkTelegramAccount:
    def __init__(
        self,
        user_gateway: UserGateway,
        social_identity_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.social_identity_gateway = social_identity_gateway
        self.user_gateway = user_gateway
        self.uow = uow
        self.current_user_provider = current_user_provider

    async def __call__(self, data: LinkTelegramAccountInput) -> None:
        provider_id = str(data.user_id)
        current_user = await self.current_user_provider.require_user()

        current_telegram = await self.social_identity_gateway.get_by_provider(
            current_user.id, "telegram"
        )
        if current_telegram is not None:
            if current_telegram.provider_id == provider_id:
                return
            raise UserAlreadyHasTelegramLinked

        linked_user = await self.user_gateway.get_by_social_identity(
            provider_name="telegram", provider_account_id=provider_id
        )
        if linked_user is not None and linked_user.id != current_user.id:
            raise TelegramAlreadyLinkedToAnotherUser

        await self.social_identity_gateway.add(
            SocialIdentity(
                id=generate_social_identity_id(),
                user_id=current_user.id,
                provider="telegram",
                provider_id=provider_id,
            )
        )
        await self.uow.commit()
        logger.info(
            "Telegram account linked",
            extra={"actor_id": str(current_user.id), "provider_id": provider_id},
        )
