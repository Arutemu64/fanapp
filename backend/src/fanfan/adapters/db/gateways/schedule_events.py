from sqlalchemy import Select, and_, delete, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from fanfan.adapters.db.models import (
    ScheduleEventORM,
    SubscriptionORM,
)
from fanfan.core.dto.page import Pagination
from fanfan.core.dto.schedule import ScheduleEventFullDTO, ScheduleEventSubscriptionDTO
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


def _parse_schedule_event_full_dto(
    event_orm: ScheduleEventORM, subscription_orm: SubscriptionORM | None
) -> ScheduleEventFullDTO:
    return ScheduleEventFullDTO(
        id=event_orm.id,
        public_number=event_orm.public_id,
        title=event_orm.title,
        duration=event_orm.duration,
        order=event_orm.order,
        is_current=event_orm.is_current,
        is_skipped=event_orm.is_skipped,
        nomination_title=event_orm.nomination_title,
        block_title=event_orm.block_title,
        queue=event_orm.queue,
        time_until=event_orm.time_until,
        user_subscription=ScheduleEventSubscriptionDTO(
            id=subscription_orm.id,
            counter=subscription_orm.counter,
        )
        if subscription_orm
        else None,
    )


def _filter_schedule_events(
    stmt: Select,
    search_query: str | None,
) -> Select:
    filters = []
    if search_query:
        filters.append(ScheduleEventORM.title.ilike(f"%{search_query}%"))
        filters.append(ScheduleEventORM.nomination_title.ilike(f"%{search_query}%"))
        if search_query.isnumeric():
            filters.append(ScheduleEventORM.public_id == int(search_query))

    return stmt.where(or_(*filters))


class ScheduleEventGateway:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_event(self, event: ScheduleEvent) -> ScheduleEvent:
        event_orm = ScheduleEventORM.from_model(event)
        self.session.add(event_orm)
        await self.session.flush([event_orm])
        return event_orm.to_model()

    async def get_event_by_id(self, event_id: ScheduleEventId) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .where(ScheduleEventORM.id == event_id)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return event_orm.to_model() if event_orm else None

    async def get_current_event(self) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .where(ScheduleEventORM.is_current.is_(True))
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return event_orm.to_model() if event_orm else None

    async def get_all_events(self) -> list[ScheduleEvent]:
        stmt = select(ScheduleEventORM).with_for_update()
        event_orm = await self.session.scalars(stmt)
        return [e.to_model() for e in event_orm]

    async def get_next_by_order(self, order: float) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .order_by(ScheduleEventORM.order)
            .where(ScheduleEventORM.order > order)
            .limit(1)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return event_orm.to_model() if event_orm else None

    async def get_previous_by_order(self, order: float) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .order_by(ScheduleEventORM.order)
            .where(ScheduleEventORM.order < order)
            .limit(1)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return event_orm.to_model() if event_orm else None

    async def save_event(self, event: ScheduleEvent) -> ScheduleEvent:
        event_orm = await self.session.merge(ScheduleEventORM.from_model(event))
        await self.session.flush([event_orm])
        return event_orm.to_model()

    async def delete_event(self, event: ScheduleEvent) -> None:
        await self.session.execute(
            delete(ScheduleEventORM).where(ScheduleEventORM.id == event.id)
        )

    async def read_event_by_id(
        self,
        event_id: ScheduleEventId,
        user_id: UserId | None = None,
    ) -> ScheduleEventFullDTO | None:
        stmt = _select_schedule_event_full_dto(user_id=user_id).where(
            ScheduleEventORM.id == event_id
        )
        result = (await self.session.execute(stmt)).first()
        if result:
            event_orm, subscription_orm = result
            return _parse_schedule_event_full_dto(
                event_orm=event_orm, subscription_orm=subscription_orm
            )
        return None

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
            return _parse_schedule_event_full_dto(
                event_orm=event_orm, subscription_orm=subscription_orm
            )
        return None

    async def read_event_user_by_id(
        self, event_id: ScheduleEventId, user_id: UserId
    ) -> ScheduleEventFullDTO | None:
        stmt = _select_schedule_event_full_dto(user_id).where(
            ScheduleEventORM.id == event_id
        )
        result = (await self.session.execute(stmt)).first()
        if result:
            event_orm, subscription_orm = result
            return _parse_schedule_event_full_dto(
                event_orm=event_orm, subscription_orm=subscription_orm
            )
        return None

    async def read_event_by_queue(self, queue: int) -> ScheduleEventFullDTO | None:
        stmt = _select_schedule_event_full_dto(None).where(
            ScheduleEventORM.queue == queue
        )
        result = (await self.session.execute(stmt)).first()
        if result:
            event_orm, subscription_orm = result
            return _parse_schedule_event_full_dto(
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
            return _parse_schedule_event_full_dto(
                event_orm=event_orm, subscription_orm=subscription_orm
            )
        return None

    async def read_list_schedule(
        self,
        user_id: UserId | None,
        pagination: Pagination | None = None,
        search_query: str | None = None,
        only_subscribed: bool = False,
    ) -> list[ScheduleEventFullDTO]:
        stmt = _select_schedule_event_full_dto(user_id).order_by(ScheduleEventORM.order)

        if search_query:
            stmt = _filter_schedule_events(stmt, search_query)
        if pagination:
            stmt = stmt.limit(pagination.limit).offset(pagination.offset)
        if only_subscribed:
            stmt = stmt.where(SubscriptionORM.id.is_not(None))

        results = (await self.session.execute(stmt)).all()

        return [
            _parse_schedule_event_full_dto(
                event_orm=event_orm, subscription_orm=subscription_orm
            )
            for event_orm, subscription_orm in results
        ]

    async def count_events(
        self,
        search_query: str | None = None,
    ) -> int:
        stmt = select(func.count(ScheduleEventORM.id))
        if search_query:
            stmt = _filter_schedule_events(stmt, search_query)
        return await self.session.scalar(stmt)
