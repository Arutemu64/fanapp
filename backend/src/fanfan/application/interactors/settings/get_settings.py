from fanfan.application.dto.settings import AppSettingsDTO, AppSettingsFieldsDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.etag import compute_strong_etag
from fanfan.application.services.permissions import PermissionService
from fanfan.core.models.app_settings import AppSettings
from fanfan.core.vo.permission import Permission


def read_app_settings(settings: AppSettings) -> AppSettingsDTO:
    # The tag covers only what this resource shows, so a schedule-settings or
    # voting-range edit to the same row does not turn an open settings form stale.
    fields = AppSettingsFieldsDTO.model_validate(settings)
    return AppSettingsDTO(
        **fields.model_dump(),
        etag=compute_strong_etag(fields.model_dump_json()),
    )


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

        return read_app_settings(await self.app_settings_gateway.get())
