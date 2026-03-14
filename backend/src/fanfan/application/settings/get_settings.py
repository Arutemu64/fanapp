from fanfan.adapters.db.gateways.app_settings import SettingsGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.settings import SettingsNotFound
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.app_settings import AppSettings
from fanfan.core.vo.user import UserRole


class GetSettings:
    def __init__(
        self,
        settings_gateway: SettingsGateway,
        user_gateway: UserGateway,
        id_provider: IdProvider,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.user_gateway = user_gateway
        self.id_provider = id_provider

    async def __call__(self) -> AppSettings:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated

        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound

        if current_user.role is not UserRole.ORG:
            raise AccessDenied

        if settings := await self.settings_gateway.get_settings():
            return settings
        raise SettingsNotFound
