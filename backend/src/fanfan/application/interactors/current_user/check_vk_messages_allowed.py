from fanfan.application.dto.user import VkMessagesStatusDTO
from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.ports.vk_messages import VkMessagesPermission
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.core.exceptions.users import SocialAccountNotLinked
from fanfan.core.vo.social_identity import SocialProvider

# Each check spends a call from the community's API quota, shared with sending.
VK_MESSAGES_CHECK_COOLDOWN_SECONDS = 5


class CheckVkMessagesAllowed:
    """Ask VK whether its community may message the current user, and store it.

    The answer is not pushed to us, so the profile asks when it opens and after
    the user returns from the community chat.
    """

    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        social_identity_gateway: SocialIdentityGateway,
        vk_messages_permission: VkMessagesPermission,
        cooldown: Cooldown,
        uow: UnitOfWork,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.social_identity_gateway = social_identity_gateway
        self.vk_messages_permission = vk_messages_permission
        self.cooldown = cooldown
        self.uow = uow

    async def __call__(self) -> VkMessagesStatusDTO:
        user_id = await self.current_user_provider.require_user_id()
        identity = await self.social_identity_gateway.get_by_provider(
            user_id=user_id, provider=SocialProvider.VK
        )
        if identity is None:
            raise SocialAccountNotLinked
        # Release the row lock before the network call.
        await self.uow.commit()

        claim = self.cooldown.claim(
            f"vk_messages_check:{user_id}", VK_MESSAGES_CHECK_COOLDOWN_SECONDS
        )
        try:
            async with claim:
                allowed = await self.vk_messages_permission.is_allowed(
                    identity.provider_user_id
                )
        except CooldownActive:
            return VkMessagesStatusDTO(messages_allowed=identity.messages_allowed)

        if identity.record_messages_allowed(allowed=allowed):
            await self.social_identity_gateway.save(identity)
            await self.uow.commit()
        return VkMessagesStatusDTO(messages_allowed=allowed)
