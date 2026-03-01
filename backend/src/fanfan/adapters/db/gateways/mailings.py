from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import MailingORM
from fanfan.core.dto.mailing import MailingDTO
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId


def _parse_mailing_dto(mailing_orm: MailingORM) -> MailingDTO:
    return MailingDTO(
        id=mailing_orm.id,
        total=mailing_orm.total,
        is_cancelled=mailing_orm.is_cancelled,
        by_user_id=mailing_orm.by_user_id,
    )


class MailingGateway:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_mailing(self, mailing: Mailing) -> Mailing:
        mailing_orm = MailingORM.from_model(mailing)
        self.session.add(mailing_orm)
        await self.session.flush([mailing_orm])
        return mailing_orm.to_model()

    async def get_mailing(self, mailing_id: MailingId, lock: bool) -> Mailing | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id)
        if lock:
            stmt = stmt.with_for_update()
        mailing_orm = await self.session.scalar(stmt)
        return mailing_orm.to_model() if mailing_orm else None

    async def save_mailing(self, mailing: Mailing) -> Mailing:
        mailing_orm = MailingORM.from_model(mailing)
        mailing_orm = await self.session.merge(mailing_orm)
        return mailing_orm.to_model()

    async def delete_mailing(self, mailing: Mailing) -> None:
        stmt = delete(MailingORM).where(MailingORM.id == mailing.id)
        await self.session.execute(stmt)

    async def read_mailing(self, mailing_id: MailingId) -> MailingDTO | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id)
        mailing_orm = await self.session.scalar(stmt)
        return _parse_mailing_dto(mailing_orm) if mailing_orm else None
