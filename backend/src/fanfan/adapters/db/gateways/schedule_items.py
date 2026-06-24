from sqlalchemy import Select, and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from fanfan.adapters.db.mappers.schedule_item import ScheduleItemMapper
from fanfan.adapters.db.models import ScheduleItemORM
from fanfan.application.dto.schedule import ScheduleItemFullDTO
from fanfan.application.ports.gateways import ScheduleItemGateway
from fanfan.core.models.schedule_item import (
    ScheduleItem,
)
from fanfan.core.vo.schedule_item import ScheduleItemId


def _select_schedule_item_full_dto() -> Select:
    return select(ScheduleItemORM).options(
        undefer(ScheduleItemORM.queue),
        undefer(ScheduleItemORM.time_until),
    )


class SqlScheduleItemGateway(ScheduleItemGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = ScheduleItemMapper()

    async def add(self, event: ScheduleItem) -> None:
        event_orm = self.mapper.from_model(event)
        self.session.add(event_orm)

    async def get_by_id(self, schedule_item_id: ScheduleItemId) -> ScheduleItem | None:
        stmt = (
            select(ScheduleItemORM)
            .where(ScheduleItemORM.id == schedule_item_id)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def get_by_queue(self, queue: int) -> ScheduleItem | None:
        stmt = (
            select(ScheduleItemORM)
            .where(ScheduleItemORM.queue == queue)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def get_current(self) -> ScheduleItem | None:
        stmt = (
            select(ScheduleItemORM)
            .where(ScheduleItemORM.is_current.is_(True))
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def get_next(self) -> ScheduleItem | None:
        current_event_order = (
            select(ScheduleItemORM.order)
            .where(ScheduleItemORM.is_current.is_(True))
            .scalar_subquery()
        )
        stmt = (
            select(ScheduleItemORM)
            .order_by(ScheduleItemORM.order)
            .where(
                and_(
                    ScheduleItemORM.order > current_event_order,
                    ScheduleItemORM.is_skipped.is_not(True),
                )
            )
            .limit(1)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def list_all(self) -> list[ScheduleItem]:
        stmt = select(ScheduleItemORM).with_for_update()
        event_orm = await self.session.scalars(stmt)
        return [self.mapper.to_model(e) for e in event_orm]

    async def get_next_by_order(self, order: float) -> ScheduleItem | None:
        stmt = (
            select(ScheduleItemORM)
            .order_by(ScheduleItemORM.order)
            .where(ScheduleItemORM.order > order)
            .limit(1)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def get_previous_by_order(self, order: float) -> ScheduleItem | None:
        stmt = (
            select(ScheduleItemORM)
            .order_by(ScheduleItemORM.order)
            .where(ScheduleItemORM.order < order)
            .limit(1)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(event_orm) if event_orm else None

    async def save(self, event: ScheduleItem) -> None:
        event_orm = await self.session.merge(self.mapper.from_model(event))
        await self.session.flush([event_orm])
        return

    async def delete(self, event: ScheduleItem) -> None:
        await self.session.execute(
            delete(ScheduleItemORM).where(ScheduleItemORM.id == event.id)
        )

    # Read projections (return DTOs, not aggregates)
    async def read_next_event(self) -> ScheduleItemFullDTO | None:
        current_event_order = (
            select(ScheduleItemORM.order)
            .where(ScheduleItemORM.is_current.is_(True))
            .scalar_subquery()
        )
        stmt = (
            _select_schedule_item_full_dto()
            .order_by(ScheduleItemORM.order)
            .where(
                and_(
                    ScheduleItemORM.order > current_event_order,
                    ScheduleItemORM.is_skipped.is_not(True),
                )
            )
            .limit(1)
        )
        event_orm = await self.session.scalar(stmt)
        if event_orm:
            return self.mapper.parse_full_dto(
                event_orm=event_orm,
                queue=event_orm.queue,
                time_until=event_orm.time_until,
            )
        return None

    async def read_current_event(self) -> ScheduleItemFullDTO | None:
        stmt = _select_schedule_item_full_dto().where(
            ScheduleItemORM.is_current.is_(True)
        )
        event_orm = await self.session.scalar(stmt)
        if event_orm:
            return self.mapper.parse_full_dto(
                event_orm=event_orm,
                queue=event_orm.queue,
                time_until=event_orm.time_until,
            )
        return None

    async def read_list_schedule(self) -> list[ScheduleItemFullDTO]:
        # The whole schedule is read uncached, so queue/time_until come from a
        # single ranking subquery joined once here, rather than the per-row
        # correlated column_properties (which would re-run the window for every
        # one of the ~hundreds of rows).
        ranked = ScheduleItemORM.ranking_subquery()
        stmt = (
            select(ScheduleItemORM, ranked.c.queue, ranked.c.time_until)
            .outerjoin(ranked, ScheduleItemORM.id == ranked.c.id)
            .order_by(ScheduleItemORM.order)
        )
        results = (await self.session.execute(stmt)).all()
        return [
            self.mapper.parse_full_dto(
                event_orm=event_orm,
                queue=queue,
                time_until=time_until,
            )
            for event_orm, queue, time_until in results
        ]
