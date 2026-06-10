from fanfan.application.dto.user import UserSocialAccountDTO
from fanfan.application.ports.gateways.social_ids import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider


class GetCurrentUserSocialIds:
    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        social_id_gateway: SocialIdentityGateway,
    ) -> None:
        self.social_id_gateway = social_id_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self) -> list[UserSocialAccountDTO]:
        current_user = await self.current_user_provider.require_user()
        return await self.social_id_gateway.read_user_social_accounts(current_user.id)
