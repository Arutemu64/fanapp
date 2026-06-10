from fanfan.application.dto.user import CurrentUserDTO
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import UserNotFound


class GetCurrentUser:
    def __init__(
        self,
        user_query: UserGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.user_query = user_query
        self.current_user_provider = current_user_provider

    async def __call__(self) -> CurrentUserDTO:
        current_user_id = await self.current_user_provider.require_user_id()
        user = await self.user_query.read_current_user(current_user_id)
        if user is None:
            raise UserNotFound
        return user
