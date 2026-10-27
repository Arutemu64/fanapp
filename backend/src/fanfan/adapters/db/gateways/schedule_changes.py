from typing import override

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.adapters.db.user_ref import parse_user_ref
from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.schedule_change import (
    ScheduleChangeEntryDTO,
    ScheduleChangeFullDTO,
)
from fanfan.application.ports.gateways import ScheduleChangeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.schedule_change import (
    ScheduleChange,
)
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.user import UserId


def _from_model(model: ScheduleChange) -> ScheduleChangeORM:
    return ScheduleChangeORM(
        id=model.id,
        type=model.type,
        mailing_id=model.mailing_id,
        user_id=model.user_id,
        changed_event_id=model.changed_event_id,
        related_entry_id=model.related_entry_id,
        next_event_changed=model.next_event_changed,
    )


def _to_model(orm: ScheduleChangeORM) -> ScheduleChange:
    return ScheduleChange(
        id=ScheduleChangeId(orm.id),
        type=orm.type,
        mailing_id=MailingId(orm.mailing_id) if orm.mailing_id is not None else None,
        user_id=UserId(orm.user_id) if orm.user_id is not None else None,
        changed_event_id=ScheduleEntryId(orm.changed_event_id)
        if orm.changed_event_id is not None
        else None,
        related_entry_id=ScheduleEntryId(orm.related_entry_id)
        if orm.related_entry_id is not None
        else None,
        next_event_changed=orm.next_event_changed,
    )


def _parse_full_dto(
    schedule_change_orm: ScheduleChangeORM,
) -> ScheduleChangeFullDTO:
    return ScheduleChangeFullDTO(
        id=ScheduleChangeId(schedule_change_orm.id),
        type=schedule_change_orm.type,
        mailing_id=MailingId(schedule_change_orm.mailing_id)
        if schedule_change_orm.mailing_id is not None
        else None,
        next_event_changed=schedule_change_orm.next_event_changed,
        changed_event=ScheduleChangeEntryDTO(
            id=ScheduleEntryId(schedule_change_orm.changed_event.id),
            type=schedule_change_orm.changed_event.type,
            number=schedule_change_orm.changed_event.number,
            title=schedule_change_orm.changed_event.title,
            order=schedule_change_orm.changed_event.order,
        )
        if schedule_change_orm.changed_event
        else None,
        related_entry=ScheduleChangeEntryDTO(
            id=ScheduleEntryId(schedule_change_orm.related_entry.id),
            type=schedule_change_orm.related_entry.type,
            number=schedule_change_orm.related_entry.number,
            title=schedule_change_orm.related_entry.title,
            order=schedule_change_orm.related_entry.order,
        )
        if schedule_change_orm.related_entry
        else None,
        user=parse_user_ref(schedule_change_orm.user)
        if schedule_change_orm.user
        else None,
        created_at=schedule_change_orm.created_at,
    )


class SqlScheduleChangeGateway(ScheduleChangeGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self.session = session
        self.uow = uow

    @override
    async def add(self, change: ScheduleChange) -> None:
        change_orm = _from_model(change)
        change_orm.created_at = func.clock_timestamp()
        self.session.add(change_orm)
        self.uow.register(change)

    @override
    async def get_by_id(self, change_id: ScheduleChangeId) -> ScheduleChange | None:
        stmt = (
            select(ScheduleChangeORM)
            .where(ScheduleChangeORM.id == change_id)
            .with_for_update()
        )
        change_orm = await self.session.scalar(stmt)
        if change_orm is None:
            return None
        change = _to_model(change_orm)
        self.uow.register(change)
        return change

    @override
    async def delete(self, change: ScheduleChange) -> None:
        await self.session.execute(
            delete(ScheduleChangeORM).where(ScheduleChangeORM.id == change.id)
        )

    @override
    async def read_schedule_change(
        self, change_id: ScheduleChangeId
    ) -> ScheduleChangeFullDTO | None:
        stmt = (
            select(ScheduleChangeORM)
            .where(ScheduleChangeORM.id == change_id)
            .options(
                joinedload(ScheduleChangeORM.changed_event),
                joinedload(ScheduleChangeORM.related_entry),
                joinedload(ScheduleChangeORM.user),
            )
        )
        result = await self.session.scalar(stmt)
        return _parse_full_dto(result) if result else None

    @override
    async def read_list_schedule_changes(
        self, pagination: CursorPagination
    ) -> list[ScheduleChangeFullDTO]:
        stmt = (
            select(ScheduleChangeORM)
            .order_by(ScheduleChangeORM.created_at.desc(), ScheduleChangeORM.id.desc())
            .options(
                joinedload(ScheduleChangeORM.changed_event),
                joinedload(ScheduleChangeORM.related_entry),
                joinedload(ScheduleChangeORM.user),
            )
            .limit(pagination.fetch_limit)
        )
        if pagination.after is not None:
            stmt = stmt.where(
                rows_after(
                    ScheduleChangeORM.created_at, ScheduleChangeORM.id, pagination.after
                )
            )
        result = (await self.session.scalars(stmt)).unique()
        return [_parse_full_dto(s) for s in result]

    @override
    async def read_seconds_since_last_change(self) -> float | None:
        elapsed = func.extract(
            "epoch", func.clock_timestamp() - func.max(ScheduleChangeORM.created_at)
        )
        seconds = await self.session.scalar(select(elapsed))
        return float(seconds) if seconds is not None else None
