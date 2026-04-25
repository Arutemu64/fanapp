from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.mappers.schedule_change import ScheduleChangeMapper
from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.application.dto.schedule_change import (
    ScheduleChangeFullDTO,
)
from fanfan.application.ports.queries.schedule_changes import ScheduleChangeQuery
from fanfan.application.ports.repositories import ScheduleChangeRepository
from fanfan.core.models.schedule_change import (
    ScheduleChange,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId


class SqlScheduleChangeGateway(ScheduleChangeRepository, ScheduleChangeQuery):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = ScheduleChangeMapper()

    async def add(self, change: ScheduleChange) -> None:
        change_orm = self.mapper.from_model(change)
        self.session.add(change_orm)

    async def get_by_id(self, change_id: ScheduleChangeId) -> ScheduleChange | None:
        stmt = (
            select(ScheduleChangeORM)
            .where(ScheduleChangeORM.id == change_id)
            .with_for_update()
        )
        change_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(change_orm) if change_orm else None

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
        return self.mapper.parse_full_dto(result) if result else None

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
