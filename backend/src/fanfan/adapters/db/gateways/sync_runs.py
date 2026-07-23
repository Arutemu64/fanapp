from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.mappers.sync_run import SyncRunMapper
from fanfan.adapters.db.models import SyncRunORM
from fanfan.application.dto.sync import SyncRunDTO
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import SyncRunStatus, SyncSource


class SqlSyncRunGateway(SyncRunGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        self.mapper = SyncRunMapper()

    async def add(self, run: SyncRun) -> None:
        self.session.add(self.mapper.from_model(run))
        self.uow.register(run)

    # Read projections (return DTOs, not aggregates)
    async def read_last_completed_at(self, source: SyncSource) -> datetime | None:
        stmt = select(func.max(SyncRunORM.finished_at)).where(
            SyncRunORM.source == source,
            SyncRunORM.status == SyncRunStatus.COMPLETED,
        )
        return await self.session.scalar(stmt)

    async def read_recent_runs(
        self, source: SyncSource, limit: int
    ) -> list[SyncRunDTO]:
        stmt = (
            select(SyncRunORM)
            .where(SyncRunORM.source == source)
            .order_by(SyncRunORM.started_at.desc())
            .options(joinedload(SyncRunORM.started_by))
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return [self.mapper.parse_dto(run) for run in result]
