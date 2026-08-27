from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import MailingORM
from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserId


def _from_model(model: Mailing) -> MailingORM:
    return MailingORM(
        id=model.id,
        status=model.status,
        by_user_id=model.by_user_id,
    )


def _to_model(orm: MailingORM) -> Mailing:
    return Mailing(
        id=MailingId(orm.id),
        status=orm.status,
        by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
    )


def _parse_dto(orm: MailingORM) -> MailingDTO:
    return MailingDTO(
        id=MailingId(orm.id),
        status=orm.status,
        by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
        sent_count=orm.sent_count,
        total_count=orm.total_count,
    )


class SqlMailingGateway(MailingGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow

    async def add(self, mailing: Mailing) -> None:
        mailing_orm = _from_model(mailing)
        self.session.add(mailing_orm)
        await self.session.flush([mailing_orm])
        # Register so any event recorded on the mailing (e.g. BroadcastQueued)
        # is written to the outbox when the unit of work commits.
        self.uow.register(mailing)

    async def get(self, mailing_id: MailingId) -> Mailing | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id).with_for_update()
        mailing_orm = await self.session.scalar(stmt)
        if mailing_orm is None:
            return None
        mailing = _to_model(mailing_orm)
        self.uow.register(mailing)
        return mailing

    async def save(self, mailing: Mailing) -> None:
        mailing_orm = _from_model(mailing)
        await self.session.merge(mailing_orm)

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
        return _parse_dto(mailing_orm) if mailing_orm else None
