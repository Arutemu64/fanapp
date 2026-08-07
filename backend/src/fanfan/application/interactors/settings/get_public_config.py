from fanfan.application.dto.settings import PublicConfigDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway


class GetPublicConfig:
    """Serve the public config projection with no authentication.

    Unlike GetSettings this takes no user and runs no permission check: the
    home page needs the countdown and voting state before login, and on a cold
    or offline PWA load there may be no session at all.
    """

    def __init__(self, app_settings_gateway: AppSettingsGateway) -> None:
        self.app_settings_gateway = app_settings_gateway

    async def __call__(self) -> PublicConfigDTO:
        return PublicConfigDTO.model_validate(await self.app_settings_gateway.get())
