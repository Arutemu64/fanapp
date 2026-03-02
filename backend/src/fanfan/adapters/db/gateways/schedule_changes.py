from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.mappers.schedule_change import ScheduleChangeMapper
from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.core.dto.schedule_change import (
    ScheduleChangeFullDTO,
)
from fanfan.core.models.schedule_change import (
    ScheduleChange,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId


class ScheduleChangeGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = ScheduleChangeMapper()

    async def add_schedule_change(self, change: ScheduleChange) -> None:
        change_orm = self.mapper.from_model(change)
        self.session.add(change_orm)

    async def get_schedule_change(
        self, change_id: ScheduleChangeId
    ) -> ScheduleChange | None:
        stmt = select(ScheduleChangeORM).where(ScheduleChangeORM.id == change_id)
        change_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(change_orm) if change_orm else None

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
        return [self.mapper.parse_full_dto(s) for s in result]
