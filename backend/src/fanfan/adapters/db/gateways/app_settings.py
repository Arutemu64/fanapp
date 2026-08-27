from adaptix import Retort
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import AppSettingsORM
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.models.app_settings import AppSettings


def _from_model(model: AppSettings, retort: Retort) -> AppSettingsORM:
    return AppSettingsORM(id=1, config=retort.dump(model))


def _to_model(orm: AppSettingsORM, retort: Retort) -> AppSettings:
    return retort.load(orm.config, AppSettings)


class SqlAppSettingsGateway(AppSettingsGateway):
    def __init__(self, session: AsyncSession, retort: Retort):
        self.session = session
        self.retort = retort

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
        return _to_model(settings_orm, self.retort)

    async def save(self, settings: AppSettings) -> None:
        await self.session.merge(_from_model(settings, self.retort))
