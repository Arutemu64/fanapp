from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.app_settings import AppSettingsMapper
from fanfan.adapters.db.models import AppSettingsORM
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.models.app_settings import AppSettings


class SqlAppSettingsGateway(AppSettingsGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = AppSettingsMapper()

    async def get(self) -> AppSettings:
        stmt = select(AppSettingsORM).where(AppSettingsORM.id == 1)
        return await self._get_by_stmt(stmt)

    async def get_for_update(self) -> AppSettings:
        stmt = select(AppSettingsORM).where(AppSettingsORM.id == 1).with_for_update()
        return await self._get_by_stmt(stmt)

    async def _get_by_stmt(self, stmt) -> AppSettings:
        settings_orm = await self.session.scalar(stmt)
        if settings_orm is None:
            raise AppSettingsNotFound
        return self.mapper.to_model(settings_orm)

    async def save(self, settings: AppSettings) -> None:
        await self.session.merge(self.mapper.from_model(settings))
