from fanfan.application.dto.settings import AppSettingsDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class GetSettings:
    def __init__(
        self,
        app_settings_gateway: AppSettingsGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.app_settings_gateway = app_settings_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self) -> AppSettingsDTO:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SETTINGS_MANAGE
        )

        settings = await self.app_settings_gateway.get()
        return AppSettingsDTO(
            festival_start=settings.festival_start,
            festival_end=settings.festival_end,
            quest_enabled=settings.quest.enabled,
            quest_max_award=settings.quest.max_award,
            quest_cancel_window_minutes=settings.quest.cancel_window_minutes,
        )
