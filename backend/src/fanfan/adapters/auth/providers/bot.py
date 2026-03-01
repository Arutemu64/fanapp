from dishka.integrations.aiogram import AiogramMiddlewareData

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import AuthenticationError
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.user import UserId


class BotIdProvider(IdProvider):
    def __init__(
        self,
        middleware_data: AiogramMiddlewareData,
        user_gateway: UserGateway,
    ):
        self.middleware_data = middleware_data
        self.user_gateway = user_gateway

    async def get_current_user_id(self) -> UserId | None:
        if tg_user := self.middleware_data.get("event_from_user"):
            if user := await self.user_gateway.get_user_by_social_id(
                provider_name="telegram",
                provider_account_id=str(tg_user.id),
            ):
                return user.id
            raise UserNotFound
        raise AuthenticationError
