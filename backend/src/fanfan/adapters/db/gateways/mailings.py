from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.mailing import MailingMapper
from fanfan.adapters.db.models import MailingORM
from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.ports.queries.mailings import MailingQuery
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId


class SqlMailingGateway(MailingRepository, MailingQuery):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = MailingMapper()

    async def add(self, mailing: Mailing) -> None:
        mailing_orm = self.mapper.from_model(mailing)
        self.session.add(mailing_orm)
        await self.session.flush([mailing_orm])
        return

    async def get(self, mailing_id: MailingId) -> Mailing | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id).with_for_update()
        mailing_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(mailing_orm) if mailing_orm else None

    async def save(self, mailing: Mailing) -> None:
        mailing_orm = self.mapper.from_model(mailing)
        await self.session.merge(mailing_orm)
        return

    async def set_total(self, mailing_id: MailingId, total_count: int) -> None:
        stmt = (
            update(MailingORM)
            .where(MailingORM.id == mailing_id)
            .values(total_count=total_count)
        )
        await self.session.execute(stmt)

    async def increment_sent(self, mailing_id: MailingId, incr_by: int = 1) -> None:
        stmt = (
            update(MailingORM)
            .where(MailingORM.id == mailing_id)
            .values(sent_count=MailingORM.sent_count + incr_by)
        )
        await self.session.execute(stmt)

    async def read_mailing(self, mailing_id: MailingId) -> MailingDTO | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id)
        mailing_orm = await self.session.scalar(stmt)
        return self.mapper.parse_dto(mailing_orm) if mailing_orm else None
