from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import SyncRunORM
from fanfan.application.dto.sync import SyncRunDTO
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.sync import SyncAlreadyRunning
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import SyncRunId, SyncRunStatus, SyncSource
from fanfan.core.vo.user import UserId


def _from_model(model: SyncRun) -> SyncRunORM:
    return SyncRunORM(
        id=model.id,
        source=model.source,
        status=model.status,
        by_user_id=model.by_user_id,
        started_at=model.started_at,
        finished_at=model.finished_at,
        result=model.result,
        error=model.error,
    )


def _to_model(orm: SyncRunORM) -> SyncRun:
    return SyncRun(
        id=SyncRunId(orm.id),
        source=orm.source,
        status=orm.status,
        by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
        result=orm.result,
        error=orm.error,
    )


def _parse_dto(orm: SyncRunORM) -> SyncRunDTO:
    return SyncRunDTO(
        id=SyncRunId(orm.id),
        source=orm.source,
        status=orm.status,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
        result=orm.result,
        error=orm.error,
    )


class SqlSyncRunGateway(SyncRunGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow

    async def add(self, run: SyncRun) -> None:
        run_orm = _from_model(run)
        # Let the partial unique index decide whether another run is active
        # rather than pre-SELECTing, so two concurrent triggers can't both pass
        # the check and start duplicate sweeps.
        with translate_integrity_error({"uq_sync_runs_active": SyncAlreadyRunning}):
            self.session.add(run_orm)
            await self.session.flush([run_orm])
        # Register so a recorded SyncRequested lands in the outbox on commit.
        self.uow.register(run)

    async def get(self, run_id: SyncRunId) -> SyncRun | None:
        stmt = select(SyncRunORM).where(SyncRunORM.id == run_id).with_for_update()
        run_orm = await self.session.scalar(stmt)
        if run_orm is None:
            return None
        run = _to_model(run_orm)
        self.uow.register(run)
        return run

    async def save(self, run: SyncRun) -> None:
        run_orm = _from_model(run)
        await self.session.merge(run_orm)

    async def get_active(self, source: SyncSource) -> SyncRun | None:
        stmt = (
            select(SyncRunORM)
            .where(
                SyncRunORM.source == source,
                SyncRunORM.finished_at.is_(None),
            )
            .with_for_update()
        )
        run_orm = await self.session.scalar(stmt)
        if run_orm is None:
            return None
        run = _to_model(run_orm)
        self.uow.register(run)
        return run

    async def fail_stale(
        self, source: SyncSource, *, older_than: datetime, error: str
    ) -> int:
        # Age is measured from created_at, not started_at: a run that was
        # requested but never picked up (broker outage) has no started_at and
        # would otherwise wedge the index forever.
        stmt = (
            update(SyncRunORM)
            .where(
                SyncRunORM.source == source,
                SyncRunORM.finished_at.is_(None),
                SyncRunORM.created_at < older_than,
            )
            .values(
                status=SyncRunStatus.FAILED,
                # DB clock: this is a bulk UPDATE with no domain logic, and the
                # moment we noticed is the best "finished" time available — when
                # the worker actually died is unknowable.
                finished_at=func.now(),
                error=error,
            )
            .returning(SyncRunORM.id)
        )
        reaped = await self.session.scalars(stmt)
        return len(reaped.all())

    async def read_latest_by_source(self) -> dict[SyncSource, SyncRunDTO]:
        stmt = (
            select(SyncRunORM)
            .distinct(SyncRunORM.source)
            .order_by(SyncRunORM.source, SyncRunORM.created_at.desc())
        )
        rows = await self.session.scalars(stmt)
        return {row.source: _parse_dto(row) for row in rows}
