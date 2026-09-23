from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.application.dto.page import Pagination
from fanfan.application.dto.schedule_change import (
    ScheduleChangeEventDTO,
    ScheduleChangeFullDTO,
    ScheduleChangeUserDTO,
)
from fanfan.application.ports.gateways import ScheduleChangeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.schedule_change import (
    ScheduleChange,
)
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.user import UserId


def _from_model(model: ScheduleChange) -> ScheduleChangeORM:
    return ScheduleChangeORM(
        id=model.id,
        type=model.type,
        mailing_id=model.mailing_id,
        user_id=model.user_id,
        changed_event_id=model.changed_event_id,
        argument_event_id=model.argument_event_id,
        next_event_changed=model.next_event_changed,
    )


def _to_model(orm: ScheduleChangeORM) -> ScheduleChange:
    return ScheduleChange(
        id=ScheduleChangeId(orm.id),
        type=orm.type,
        mailing_id=MailingId(orm.mailing_id) if orm.mailing_id is not None else None,
        user_id=UserId(orm.user_id) if orm.user_id is not None else None,
        changed_event_id=ScheduleEventId(orm.changed_event_id)
        if orm.changed_event_id is not None
        else None,
        argument_event_id=ScheduleEventId(orm.argument_event_id)
        if orm.argument_event_id is not None
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
        user_id=UserId(schedule_change_orm.user_id)
        if schedule_change_orm.user_id is not None
        else None,
        next_event_changed=schedule_change_orm.next_event_changed,
        changed_event=ScheduleChangeEventDTO(
            id=ScheduleEventId(schedule_change_orm.changed_event.id),
            number=schedule_change_orm.changed_event.number,
            title=schedule_change_orm.changed_event.title,
            order=schedule_change_orm.changed_event.order,
        )
        if schedule_change_orm.changed_event
        else None,
        argument_event=ScheduleChangeEventDTO(
            id=ScheduleEventId(schedule_change_orm.argument_event.id),
            number=schedule_change_orm.argument_event.number,
            title=schedule_change_orm.argument_event.title,
            order=schedule_change_orm.argument_event.order,
        )
        if schedule_change_orm.argument_event
        else None,
        user=ScheduleChangeUserDTO(
            id=UserId(schedule_change_orm.user.id),
            username=schedule_change_orm.user.username,
        )
        if schedule_change_orm.user
        else None,
    )


class SqlScheduleChangeGateway(ScheduleChangeGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self.session = session
        self.uow = uow

    async def add(self, change: ScheduleChange) -> None:
        change_orm = _from_model(change)
        # Insert time, not the column's now() default: now() is the transaction
        # start, which precedes the lock_for_edit wait, so it would backdate the
        # change and shorten the announcement cooldown measured from it.
        change_orm.created_at = func.clock_timestamp()
        self.session.add(change_orm)
        self.uow.register(change)

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

    async def delete(self, change: ScheduleChange) -> None:
        await self.session.execute(
            delete(ScheduleChangeORM).where(ScheduleChangeORM.id == change.id)
        )

    async def read_schedule_change(
        self, change_id: ScheduleChangeId
    ) -> ScheduleChangeFullDTO | None:
        stmt = (
            select(ScheduleChangeORM)
            .where(ScheduleChangeORM.id == change_id)
            .options(
                joinedload(ScheduleChangeORM.changed_event),
                joinedload(ScheduleChangeORM.argument_event),
                joinedload(ScheduleChangeORM.user),
            )
        )
        result = await self.session.scalar(stmt)
        return _parse_full_dto(result) if result else None

    async def read_list_schedule_changes(
        self, pagination: Pagination
    ) -> list[ScheduleChangeFullDTO]:
        stmt = (
            select(ScheduleChangeORM)
            # id (uuid7, time-ordered) breaks created_at ties so a stable total
            # order holds across offset pages — a bulk schedule edit inserts many
            # change rows in one transaction sharing created_at, which would
            # otherwise shift between pages and let a change slip through unseen.
            .order_by(ScheduleChangeORM.created_at.desc(), ScheduleChangeORM.id.desc())
            .options(
                joinedload(ScheduleChangeORM.changed_event),
                joinedload(ScheduleChangeORM.argument_event),
                joinedload(ScheduleChangeORM.user),
            )
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        result = (await self.session.scalars(stmt)).unique()
        return [_parse_full_dto(s) for s in result]

    async def read_seconds_since_last_change(self) -> float | None:
        # clock_timestamp(), not now(): now() is frozen at the start of this
        # transaction, which may predate the lock wait behind the edit whose
        # row we are measuring from.
        elapsed = func.extract(
            "epoch", func.clock_timestamp() - func.max(ScheduleChangeORM.created_at)
        )
        seconds = await self.session.scalar(select(elapsed))
        return float(seconds) if seconds is not None else None
