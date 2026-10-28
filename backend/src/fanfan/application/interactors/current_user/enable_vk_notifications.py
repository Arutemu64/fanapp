import logging

from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.ports.vk_messages import VkMessagesPermission
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.notifications import (
    NotificationsCheckTooFast,
    VkMessagesNotAllowed,
)
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.core.exceptions.users import SocialAccountNotLinked
from fanfan.core.vo.social_identity import SocialProvider

logger = logging.getLogger(__name__)

# Each check spends a call from the community's API quota, shared with sending.
NOTIFICATIONS_CHECK_COOLDOWN_SECONDS = 3


class EnableVkNotifications:
    """Turn VK notifications on, but only once VK lets the community write."""

    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        social_identity_gateway: SocialIdentityGateway,
        user_gateway: UserGateway,
        vk_messages_permission: VkMessagesPermission,
        cooldown: Cooldown,
        uow: UnitOfWork,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.social_identity_gateway = social_identity_gateway
        self.user_gateway = user_gateway
        self.vk_messages_permission = vk_messages_permission
        self.cooldown = cooldown
        self.uow = uow

    async def __call__(self) -> None:
        user = await self.current_user_provider.require_user()
        identity = await self.social_identity_gateway.get_by_provider(
            user_id=user.id, provider=SocialProvider.VK
        )
        if identity is None:
            raise SocialAccountNotLinked

        claim = self.cooldown.claim(
            f"vk_messages_check:{user.id}", NOTIFICATIONS_CHECK_COOLDOWN_SECONDS
        )
        try:
            async with claim:
                allowed = await self.vk_messages_permission.is_allowed(
                    identity.provider_user_id
                )
        except CooldownActive as e:
            raise NotificationsCheckTooFast(retry_after=e.details["retry_after"]) from e
        if not allowed:
            raise VkMessagesNotAllowed

        user.update_settings(receive_vk_notifications=True)
        await self.user_gateway.save(user)
        await self.uow.commit()
        logger.info("VK notifications switched on", extra={"user_id": str(user.id)})
