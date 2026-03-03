from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.mailing import MailingMapper
from fanfan.adapters.db.models import MailingORM
from fanfan.core.dto.mailing import MailingDTO
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId


class MailingGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = MailingMapper()

    async def add_mailing(self, mailing: Mailing) -> Mailing:
        mailing_orm = self.mapper.from_model(mailing)
        self.session.add(mailing_orm)
        await self.session.flush([mailing_orm])
        return self.mapper.to_model(mailing_orm)

    async def get_mailing(self, mailing_id: MailingId, lock: bool) -> Mailing | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id)
        if lock:
            stmt = stmt.with_for_update()
        mailing_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(mailing_orm) if mailing_orm else None

    async def save_mailing(self, mailing: Mailing) -> Mailing:
        mailing_orm = self.mapper.from_model(mailing)
        mailing_orm = await self.session.merge(mailing_orm)
        return self.mapper.to_model(mailing_orm)

    async def delete_mailing(self, mailing: Mailing) -> None:
        stmt = delete(MailingORM).where(MailingORM.id == mailing.id)
        await self.session.execute(stmt)

    async def read_mailing(self, mailing_id: MailingId) -> MailingDTO | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id)
        mailing_orm = await self.session.scalar(stmt)
        return self.mapper.parse_dto(mailing_orm) if mailing_orm else None
