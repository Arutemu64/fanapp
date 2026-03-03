from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.app_settings import AppSettingsMapper
from fanfan.adapters.db.models import AppSettingsORM
from fanfan.core.models.app_settings import AppSettings


class SettingsGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = AppSettingsMapper()

    async def add_settings(self, settings: AppSettings) -> AppSettings:
        settings_orm = self.mapper.from_model(settings)
        self.session.add(settings_orm)
        await self.session.flush([settings_orm])
        return self.mapper.to_model(settings_orm)

    async def get_settings(self) -> AppSettings | None:
        stmt = select(AppSettingsORM).where(AppSettingsORM.id == 1)
        settings_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(settings_orm) if settings_orm else None

    async def save_settings(self, settings: AppSettings):
        await self.session.merge(self.mapper.from_model(settings))
