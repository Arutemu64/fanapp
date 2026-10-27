from sqlalchemy import Select, and_, delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from fanfan.adapters.db.models import (
    ScheduleBlockStartORM,
    ScheduleEntryORM,
    ScheduleEventORM,
)
from fanfan.application.dto.schedule import (
    ScheduleBlockStartDTO,
    ScheduleEntryDTO,
    ScheduleEventFullDTO,
)
from fanfan.application.ports.gateways import ScheduleEntryGateway
from fanfan.core.models.schedule_entry import (
    ScheduleBlockStart,
    ScheduleEntry,
    ScheduleEvent,
)
from fanfan.core.vo.schedule_entry import ScheduleEntryId, ScheduleEntryType

SCHEDULE_EDIT_LOCK_KEY = "schedule:edit"


def _from_model(model: ScheduleEntry) -> ScheduleEntryORM:
    if isinstance(model, ScheduleBlockStart):
        return ScheduleBlockStartORM(
            id=model.id,
            title=model.title,
            order=model.order,
            number=None,
            duration=0,
            is_current=False,
            is_skipped=False,
            nomination_title=None,
        )
    return ScheduleEventORM(
        id=model.id,
        number=model.number,
        title=model.title,
        duration=model.duration,
        is_current=model.is_current,
        is_skipped=model.is_skipped,
        order=model.order,
        nomination_title=model.nomination_title,
    )


def _event_to_model(orm: ScheduleEntryORM) -> ScheduleEvent:
    return ScheduleEvent(
        id=ScheduleEntryId(orm.id),
        number=orm.number,
        title=orm.title,
        duration=orm.duration,
        is_current=orm.is_current,
        is_skipped=orm.is_skipped,
        order=orm.order,
        nomination_title=orm.nomination_title,
    )


def _to_model(orm: ScheduleEntryORM) -> ScheduleEntry:
    if isinstance(orm, ScheduleBlockStartORM):
        return ScheduleBlockStart(
            id=ScheduleEntryId(orm.id), title=orm.title, order=orm.order
        )
    return _event_to_model(orm)


def _parse_event_dto(
    event_orm: ScheduleEntryORM,
    *,
    position: int | None,
) -> ScheduleEventFullDTO:
    return ScheduleEventFullDTO(
        type=ScheduleEntryType.EVENT,
        id=ScheduleEntryId(event_orm.id),
        number=event_orm.number,
        title=event_orm.title,
        duration=event_orm.duration,
        order=event_orm.order,
        is_current=event_orm.is_current,
        is_skipped=event_orm.is_skipped,
        nomination_title=event_orm.nomination_title,
        position=position,
    )


def _parse_entry_dto(
    entry_orm: ScheduleEntryORM,
    *,
    position: int | None,
) -> ScheduleEntryDTO:
    if isinstance(entry_orm, ScheduleBlockStartORM):
        return ScheduleBlockStartDTO(
            type=ScheduleEntryType.BLOCK_START,
            id=ScheduleEntryId(entry_orm.id),
            title=entry_orm.title,
            order=entry_orm.order,
        )
    return _parse_event_dto(entry_orm, position=position)


def _select_schedule_event_full_dto() -> Select[ScheduleEventORM]:
    return select(ScheduleEventORM).options(
        undefer(ScheduleEventORM.position),
    )


class SqlScheduleEntryGateway(ScheduleEntryGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_for_edit(self) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": SCHEDULE_EDIT_LOCK_KEY},
        )

    async def add(self, entry: ScheduleEntry) -> None:
        entry_orm = _from_model(entry)
        self.session.add(entry_orm)

    async def get_entry(self, entry_id: ScheduleEntryId) -> ScheduleEntry | None:
        stmt = (
            select(ScheduleEntryORM)
            .where(ScheduleEntryORM.id == entry_id)
            .with_for_update()
        )
        entry_orm = await self.session.scalar(stmt)
        return _to_model(entry_orm) if entry_orm else None

    async def get_event(self, event_id: ScheduleEntryId) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .where(ScheduleEventORM.id == event_id)
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return _event_to_model(event_orm) if event_orm else None

    async def get_first(self) -> ScheduleEntry | None:
        stmt = (
            select(ScheduleEntryORM)
            .order_by(ScheduleEntryORM.order)
            .limit(1)
            .with_for_update()
        )
        entry_orm = await self.session.scalar(stmt)
        return _to_model(entry_orm) if entry_orm else None

    async def get_current(self) -> ScheduleEvent | None:
        stmt = (
            select(ScheduleEventORM)
            .where(ScheduleEventORM.is_current.is_(True))
            .with_for_update()
        )
        event_orm = await self.session.scalar(stmt)
        return _event_to_model(event_orm) if event_orm else None

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
        return _event_to_model(event_orm) if event_orm else None

    async def list_all(self) -> list[ScheduleEntry]:
        stmt = (
            select(ScheduleEntryORM).order_by(ScheduleEntryORM.order).with_for_update()
        )
        entry_orms = await self.session.scalars(stmt)
        return [_to_model(e) for e in entry_orms]

    async def get_next_by_order(self, order: float) -> ScheduleEntry | None:
        stmt = (
            select(ScheduleEntryORM)
            .order_by(ScheduleEntryORM.order)
            .where(ScheduleEntryORM.order > order)
            .limit(1)
            .with_for_update()
        )
        entry_orm = await self.session.scalar(stmt)
        return _to_model(entry_orm) if entry_orm else None

    async def get_previous_by_order(self, order: float) -> ScheduleEntry | None:
        stmt = (
            select(ScheduleEntryORM)
            .order_by(ScheduleEntryORM.order.desc())
            .where(ScheduleEntryORM.order < order)
            .limit(1)
            .with_for_update()
        )
        entry_orm = await self.session.scalar(stmt)
        return _to_model(entry_orm) if entry_orm else None

    async def save(self, entry: ScheduleEntry) -> None:
        await self.session.merge(_from_model(entry))
        await self.session.flush()

    async def delete(self, entry: ScheduleEntry) -> None:
        await self.session.execute(
            delete(ScheduleEntryORM).where(ScheduleEntryORM.id == entry.id)
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
            return _parse_event_dto(event_orm, position=event_orm.position)
        return None

    async def read_current_event(self) -> ScheduleEventFullDTO | None:
        stmt = _select_schedule_event_full_dto().where(
            ScheduleEventORM.is_current.is_(True)
        )
        event_orm = await self.session.scalar(stmt)
        if event_orm:
            return _parse_event_dto(event_orm, position=event_orm.position)
        return None

    async def read_list_schedule(self) -> list[ScheduleEntryDTO]:
        ranked = ScheduleEventORM.ranking_subquery()
        stmt = (
            select(ScheduleEntryORM, ranked.c.position)
            .outerjoin(ranked, ScheduleEntryORM.id == ranked.c.id)
            .order_by(ScheduleEntryORM.order)
        )
        results = (await self.session.execute(stmt)).all()
        return [
            _parse_entry_dto(entry_orm, position=position)
            for entry_orm, position in results
        ]
