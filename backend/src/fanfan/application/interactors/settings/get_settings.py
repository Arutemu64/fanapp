from fanfan.application.dto.settings import AppSettingsDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.vo.user import UserRole


class GetSettings:
    def __init__(
        self,
        app_settings_gateway: AppSettingsGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.app_settings_gateway = app_settings_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self) -> AppSettingsDTO:
        current_user = await self.current_user_provider.require_user()

        if current_user.role is not UserRole.ORG:
            raise AccessDenied

        return AppSettingsDTO.model_validate(await self.app_settings_gateway.get())
