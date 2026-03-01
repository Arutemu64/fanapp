from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.core.dto.user import UserFullDTO
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.user import UserId


class GetUserById:
    def __init__(self, user_gateway: UserGateway) -> None:
        self.user_gateway = user_gateway

    async def __call__(self, user_id: UserId) -> UserFullDTO:
        if user := await self.user_gateway.read_full_user_by_id(user_id):
            return user
        raise UserNotFound
