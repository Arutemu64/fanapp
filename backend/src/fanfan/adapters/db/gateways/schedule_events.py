from sqlalchemy import Select, and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from fanfan.adapters.db.mappers.schedule_event import ScheduleEventMapper
from fanfan.adapters.db.models import ScheduleEventORM
from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.ports.gateways import ScheduleEventGateway
from fanfan.core.models.schedule_event import (
    ScheduleEvent,
)
from fanfan.core.vo.schedule_event import ScheduleEventId


def _select_schedule_event_full_dto() -> Select:
    return select(ScheduleEventORM).options(
        undefer(ScheduleEventORM.queue),
    )


class SqlScheduleEventGateway(ScheduleEventGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = ScheduleEventMapper()

    async def add(self, event: ScheduleEvent) -> None:
        event_orm = self.mapper.from_model(event)
        self.session.add(event_orm)

    async def get_by_id(self, event_id: ScheduleEventId) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .where(ScheduleEventORM.id == event_id)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def get_by_queue(self, queue: int) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .where(ScheduleEventORM.queue == queue)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def get_current(self) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .where(ScheduleEventORM.is_current.is_(True))
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def get_next(self) -> ScheduleEvent | None:
        current_event_order = (
            select(ScheduleEventORM.order)
            .where(ScheduleEventORM.is_current.is_(True))
            .scalar_subquery()
        )
        stmt = (
            select(ScheduleEventORM)
            .order_by(ScheduleEventORM.order)
            .where(
                and_(
                    ScheduleEventORM.order > current_event_order,
                    ScheduleEventORM.is_skipped.is_not(True),
                )
            )
            .limit(1)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def list_all(self) -> list[ScheduleEvent]:
        stmt = select(ScheduleEventORM).with_for_update()
        event_orm = await self.session.scalars(stmt)
        return [self.mapper.to_model(e) for e in event_orm]

    async def get_next_by_order(self, order: float) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .order_by(ScheduleEventORM.order)
            .where(ScheduleEventORM.order > order)
            .limit(1)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def get_previous_by_order(self, order: float) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .order_by(ScheduleEventORM.order)
            .where(ScheduleEventORM.order < order)
            .limit(1)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def save(self, event: ScheduleEvent) -> None:
        event_orm = await self.session.merge(self.mapper.from_model(event))
        await self.session.flush([event_orm])

    async def delete(self, event: ScheduleEvent) -> None:
        await self.session.execute(
            delete(ScheduleEventORM).where(ScheduleEventORM.id == event.id)
        )

    async def read_next_event(self) -> ScheduleEventFullDTO | None:
        current_event_order = (
            select(ScheduleEventORM.order)
            .where(ScheduleEventORM.is_current.is_(True))
            .scalar_subquery()
        )
        stmt = (
            _select_schedule_event_full_dto()
            .order_by(ScheduleEventORM.order)
            .where(
                and_(
                    ScheduleEventORM.order > current_event_order,
                    ScheduleEventORM.is_skipped.is_not(True),
                )
            )
            .limit(1)
        )
        event_orm = await self.session.scalar(stmt)
        if event_orm:
            return self.mapper.parse_full_dto(
                event_orm=event_orm,
                queue=event_orm.queue,
            )
        return None

    async def read_current_event(self) -> ScheduleEventFullDTO | None:
        stmt = _select_schedule_event_full_dto().where(
            ScheduleEventORM.is_current.is_(True)
        )
        event_orm = await self.session.scalar(stmt)
        if event_orm:
            return self.mapper.parse_full_dto(
                event_orm=event_orm,
                queue=event_orm.queue,
            )
        return None

    async def read_list_schedule(self) -> list[ScheduleEventFullDTO]:
        # The whole schedule is read uncached, so queue comes from a single
        # ranking subquery joined once here, rather than the per-row correlated
        # column_property (which would re-run the window for every one of the
        # ~hundreds of rows). Absolute expected times are filled afterwards by
        # the schedule timing service (ADR-0008).
        ranked = ScheduleEventORM.ranking_subquery()
        stmt = (
            select(ScheduleEventORM, ranked.c.queue)
            .outerjoin(ranked, ScheduleEventORM.id == ranked.c.id)
            .order_by(ScheduleEventORM.order)
        )
        results = (await self.session.execute(stmt)).all()
        return [
            self.mapper.parse_full_dto(
                event_orm=event_orm,
                queue=queue,
            )
            for event_orm, queue in results
        ]
