from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.user import UserSocialAccountDTO
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound


class GetCurrentUserSocialAccounts:
    def __init__(self, user_gateway: UserGateway, id_provider: IdProvider) -> None:
        self.user_gateway = user_gateway
        self.id_provider = id_provider

    async def __call__(self) -> list[UserSocialAccountDTO]:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        return await self.user_gateway.read_current_user_social_accounts(
            current_user_id
        )
