from sqlalchemy import Select, and_, delete, false, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from fanfan.adapters.db.mappers.schedule_event import ScheduleEventMapper
from fanfan.adapters.db.models import (
    ScheduleEventORM,
    SubscriptionORM,
)
from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.ports.repositories import ScheduleEventRepository
from fanfan.core.models.schedule_event import (
    ScheduleEvent,
)
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.user import UserId


def _select_schedule_event_full_dto(user_id: UserId | None) -> Select:
    # If user_id is None, we want the join condition to always be false
    # so that the outer join returns NULL for all Subscription columns.
    user_condition = (
        (SubscriptionORM.user_id == user_id) if user_id is not None else false()
    )

    return (
        select(ScheduleEventORM, SubscriptionORM)
        .options(
            undefer(ScheduleEventORM.queue),
            undefer(ScheduleEventORM.time_until),
        )
        .outerjoin(
            SubscriptionORM,
            and_(
                SubscriptionORM.event_id == ScheduleEventORM.id,
                user_condition,
            ),
        )
    )


class SqlScheduleEventRepository(ScheduleEventRepository):
    # TODO replace some get with read?
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
        return

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
            _select_schedule_event_full_dto(None)
            .order_by(ScheduleEventORM.order)
            .where(
                and_(
                    ScheduleEventORM.order > current_event_order,
                    ScheduleEventORM.is_skipped.is_not(True),
                )
            )
            .limit(1)
        )
        result = (await self.session.execute(stmt)).first()
        if result:
            event_orm, subscription_orm = result
            return self.mapper.parse_full_dto(
                event_orm=event_orm, subscription_orm=subscription_orm
            )
        return None

    async def read_current_event(self) -> ScheduleEventFullDTO | None:
        stmt = _select_schedule_event_full_dto(None).where(
            ScheduleEventORM.is_current.is_(True)
        )
        result = (await self.session.execute(stmt)).first()
        if result:
            event_orm, subscription_orm = result
            return self.mapper.parse_full_dto(
                event_orm=event_orm, subscription_orm=subscription_orm
            )
        return None

    async def read_list_schedule(
        self, user_id: UserId | None
    ) -> list[ScheduleEventFullDTO]:
        stmt = _select_schedule_event_full_dto(user_id).order_by(ScheduleEventORM.order)
        results = (await self.session.execute(stmt)).all()
        return [
            self.mapper.parse_full_dto(
                event_orm=event_orm, subscription_orm=subscription_orm
            )
            for event_orm, subscription_orm in results
        ]
