from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.core.dto.schedule_change import (
    ScheduleChangeEventDTO,
    ScheduleChangeFullDTO,
    ScheduleChangeUserDTO,
)
from fanfan.core.models.schedule_change import (
    ScheduleChange,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId


def _parse_schedule_change_full_dto(
    schedule_change_orm: ScheduleChangeORM,
) -> ScheduleChangeFullDTO:
    return ScheduleChangeFullDTO(
        id=schedule_change_orm.id,
        type=schedule_change_orm.type,
        mailing_id=schedule_change_orm.mailing_id,
        user_id=schedule_change_orm.user_id,
        send_global_announcement=schedule_change_orm.send_global_announcement,
        changed_event=ScheduleChangeEventDTO(
            id=schedule_change_orm.changed_event.id,
            public_number=schedule_change_orm.changed_event.public_id,
            title=schedule_change_orm.changed_event.title,
        )
        if schedule_change_orm.changed_event
        else None,
        argument_event=ScheduleChangeEventDTO(
            id=schedule_change_orm.argument_event.id,
            public_number=schedule_change_orm.argument_event.public_id,
            title=schedule_change_orm.argument_event.title,
        )
        if schedule_change_orm.argument_event
        else None,
        user=ScheduleChangeUserDTO(
            id=schedule_change_orm.user.id,
            username=schedule_change_orm.user.username,
        )
        if schedule_change_orm.user
        else None,
    )


class ScheduleChangeGateway:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_schedule_change(self, change: ScheduleChange) -> ScheduleChange:
        schedule_change_orm = ScheduleChangeORM.from_model(change)
        self.session.add(schedule_change_orm)
        await self.session.flush([schedule_change_orm])
        return schedule_change_orm.to_model()

    async def get_schedule_change(
        self, change_id: ScheduleChangeId
    ) -> ScheduleChange | None:
        stmt = select(ScheduleChangeORM).where(ScheduleChangeORM.id == change_id)
        schedule_change_orm = await self.session.scalar(stmt)
        return schedule_change_orm.to_model() if schedule_change_orm else None

    async def delete_schedule_change(self, change: ScheduleChange) -> None:
        await self.session.execute(
            delete(ScheduleChangeORM).where(ScheduleChangeORM.id == change.id)
        )

    async def read_list_schedule_changes(self) -> list[ScheduleChangeFullDTO]:
        # TODO Add pagination
        stmt = (
            select(ScheduleChangeORM)
            .order_by(ScheduleChangeORM.created_at.desc())
            .options(
                joinedload(ScheduleChangeORM.changed_event),
                joinedload(ScheduleChangeORM.argument_event),
                joinedload(ScheduleChangeORM.user),
            )
        )
        result = (await self.session.scalars(stmt)).unique()
        return [_parse_schedule_change_full_dto(s) for s in result]
