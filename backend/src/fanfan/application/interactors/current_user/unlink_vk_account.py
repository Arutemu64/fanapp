import logging

from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import VkCannotBeUnlinkedWithoutEmail
from fanfan.core.vo.social_identity import SocialProvider

logger = logging.getLogger(__name__)


class UnlinkVkAccount:
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

    async def __call__(self) -> None:
        current_user = await self.current_user_provider.require_user()

        if current_user.email is None:
            raise VkCannotBeUnlinkedWithoutEmail

        vk_identity = await self.social_identity_gateway.get_by_provider(
            user_id=current_user.id,
            provider=SocialProvider.VK,
        )
        if vk_identity:
            await self.social_identity_gateway.delete(vk_identity)
            await self.uow.commit()
            logger.info(
                "VK account unlinked",
                extra={"actor_id": str(current_user.id)},
            )
