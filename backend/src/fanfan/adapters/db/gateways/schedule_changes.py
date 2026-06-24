from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.mappers.schedule_change import ScheduleChangeMapper
from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.application.dto.page import Pagination
from fanfan.application.dto.schedule_change import (
    ScheduleChangeFullDTO,
)
from fanfan.application.ports.gateways import ScheduleChangeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.schedule_change import (
    ScheduleChange,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId


class SqlScheduleChangeGateway(ScheduleChangeGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        self.mapper = ScheduleChangeMapper()

    async def add(self, change: ScheduleChange) -> None:
        change_orm = self.mapper.from_model(change)
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
        change = self.mapper.to_model(change_orm)
        self.uow.register(change)
        return change

    async def delete(self, change: ScheduleChange) -> None:
        await self.session.execute(
            delete(ScheduleChangeORM).where(ScheduleChangeORM.id == change.id)
        )

    # Read projections (return DTOs, not aggregates)
    async def read_schedule_change(
        self, change_id: ScheduleChangeId
    ) -> ScheduleChangeFullDTO | None:
        stmt = (
            select(ScheduleChangeORM)
            .where(ScheduleChangeORM.id == change_id)
            .options(
                joinedload(ScheduleChangeORM.changed_schedule_item),
                joinedload(ScheduleChangeORM.argument_schedule_item),
                joinedload(ScheduleChangeORM.user),
            )
        )
        result = await self.session.scalar(stmt)
        return self.mapper.parse_full_dto(result) if result else None

    async def read_list_schedule_changes(
        self, pagination: Pagination
    ) -> list[ScheduleChangeFullDTO]:
        stmt = (
            select(ScheduleChangeORM)
            .order_by(ScheduleChangeORM.created_at.desc())
            .options(
                joinedload(ScheduleChangeORM.changed_schedule_item),
                joinedload(ScheduleChangeORM.argument_schedule_item),
                joinedload(ScheduleChangeORM.user),
            )
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        result = (await self.session.scalars(stmt)).unique()
        return [self.mapper.parse_full_dto(s) for s in result]
