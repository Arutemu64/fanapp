from typing import override

from pydantic import TypeAdapter
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import AppSettingsORM
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.models.app_settings import AppSettings

_SETTINGS_ADAPTER = TypeAdapter(AppSettings)


def _from_model(model: AppSettings) -> AppSettingsORM:
    config = _SETTINGS_ADAPTER.dump_python(model, mode="json", exclude={"_events"})
    return AppSettingsORM(id=1, config=config)


def _to_model(orm: AppSettingsORM) -> AppSettings:
    return _SETTINGS_ADAPTER.validate_python(orm.config)


class SqlAppSettingsGateway(AppSettingsGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def get(self) -> AppSettings:
        stmt = select(AppSettingsORM).where(AppSettingsORM.id == 1)
        return await self._get_by_stmt(stmt)

    @override
    async def get_for_update(self) -> AppSettings:
        stmt = select(AppSettingsORM).where(AppSettingsORM.id == 1).with_for_update()
        return await self._get_by_stmt(stmt)

    async def _get_by_stmt(self, stmt: Select[AppSettingsORM]) -> AppSettings:
        settings_orm = await self.session.scalar(stmt)
        if settings_orm is None:
            raise AppSettingsNotFound
        return _to_model(settings_orm)

    @override
    async def save(self, settings: AppSettings) -> None:
        await self.session.merge(_from_model(settings))
