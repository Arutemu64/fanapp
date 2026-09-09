from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import MailingORM
from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserId, UserRole


def _from_model(model: Mailing) -> MailingORM:
    return MailingORM(
        id=model.id,
        status=model.status,
        by_user_id=model.by_user_id,
        body=model.body,
        roles=[r.value for r in model.roles] if model.roles is not None else None,
    )


def _to_model(orm: MailingORM) -> Mailing:
    return Mailing(
        id=MailingId(orm.id),
        status=orm.status,
        by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
        body=orm.body,
        roles=[UserRole(r) for r in orm.roles] if orm.roles is not None else None,
    )


def _parse_dto(orm: MailingORM) -> MailingDTO:
    return MailingDTO(
        id=MailingId(orm.id),
        status=orm.status,
        by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
        body=orm.body,
        roles=[UserRole(r) for r in orm.roles] if orm.roles is not None else None,
        sent_count=orm.sent_count,
        total_count=orm.total_count,
        created_at=orm.created_at,
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

    async def set_status(self, mailing_id: MailingId, status: MailingStatus) -> None:
        stmt = (
            update(MailingORM).where(MailingORM.id == mailing_id).values(status=status)
        )
        await self.session.execute(stmt)

    async def set_body(self, mailing_id: MailingId, body: str) -> None:
        stmt = update(MailingORM).where(MailingORM.id == mailing_id).values(body=body)
        await self.session.execute(stmt)

    async def set_total(self, mailing_id: MailingId, total_count: int) -> None:
        stmt = (
            update(MailingORM)
            .where(MailingORM.id == mailing_id)
            .values(total_count=total_count)
        )
        await self.session.execute(stmt)

    async def increment_sent(
        self, mailing_id: MailingId, incr_by: int = 1
    ) -> tuple[int, int]:
        # Atomic increment; RETURNING hands back the post-increment (sent, total)
        # so the caller's aggregate decides completion — the rule does not live in
        # this UPDATE.
        stmt = (
            update(MailingORM)
            .where(MailingORM.id == mailing_id)
            .values(sent_count=MailingORM.sent_count + incr_by)
            .returning(MailingORM.sent_count, MailingORM.total_count)
        )
        row = (await self.session.execute(stmt)).one()
        return row.sent_count, row.total_count

    async def read_mailing(self, mailing_id: MailingId) -> MailingDTO | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id)
        mailing_orm = await self.session.scalar(stmt)
        return _parse_dto(mailing_orm) if mailing_orm else None

    async def read_broadcasts(self, pagination: Pagination) -> list[MailingDTO]:
        # Organizer broadcasts only: a schedule-change fan-out leaves roles NULL,
        # so it never surfaces in the mailing history. The table is small (manual
        # broadcasts are infrequent), so a plain created_at sort needs no index.
        stmt = (
            select(MailingORM)
            .where(MailingORM.roles.isnot(None))
            .order_by(MailingORM.created_at.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        rows = await self.session.scalars(stmt)
        return [_parse_dto(m) for m in rows]
