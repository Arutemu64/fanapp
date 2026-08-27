from sqlalchemy import delete, select
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
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow

    async def add(self, change: ScheduleChange) -> None:
        change_orm = _from_model(change)
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
            .order_by(ScheduleChangeORM.created_at.desc())
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
