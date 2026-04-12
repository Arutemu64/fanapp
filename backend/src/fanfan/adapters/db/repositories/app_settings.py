from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.app_settings import AppSettingsMapper
from fanfan.adapters.db.models import AppSettingsORM
from fanfan.application.ports.repositories.app_settings import AppSettingsRepository
from fanfan.core.exceptions.settings import AppAppSettingsNotFound
from fanfan.core.models.app_settings import AppSettings


class SqlAppSettingsRepository(AppSettingsRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = AppSettingsMapper()

    async def get(self) -> AppSettings:
        stmt = select(AppSettingsORM).where(AppSettingsORM.id == 1)
        settings_orm = await self.session.scalar(stmt)
        if settings_orm is None:
            raise AppAppSettingsNotFound
        return self.mapper.to_model(settings_orm)

    async def save(self, settings: AppSettings) -> None:
        await self.session.merge(self.mapper.from_model(settings))
