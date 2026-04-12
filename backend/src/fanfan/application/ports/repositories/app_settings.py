from typing import Protocol

from fanfan.core.models.app_settings import AppSettings


class AppSettingsRepository(Protocol):
    async def get(self) -> AppSettings: ...
    async def save(self, settings: AppSettings) -> None: ...
