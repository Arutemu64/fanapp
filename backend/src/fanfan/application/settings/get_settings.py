from fanfan.adapters.db.gateways.app_settings import SettingsGateway
from fanfan.core.exceptions.settings import SettingsNotFound
from fanfan.core.models.app_settings import AppSettings


class GetSettings:
    def __init__(self, settings_gateway: SettingsGateway) -> None:
        self.settings_gateway = settings_gateway

    async def __call__(self) -> AppSettings:
        if settings := await self.settings_gateway.get_settings():
            return settings
        raise SettingsNotFound
