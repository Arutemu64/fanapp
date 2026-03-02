from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.user import UserId


class RawIdProvider(IdProvider):
    def __init__(self, user_id: UserId, user_gateway: UserGateway):
        self.user_id = user_id
        self.user_gateway = user_gateway

    async def get_current_user_id(self) -> UserId | None:
        if user := await self.user_gateway.get_user_by_username("system"):
            return user.id
        raise UserNotFound
