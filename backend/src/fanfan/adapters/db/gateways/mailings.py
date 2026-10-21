from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import MailingORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.dto.page import CursorPagination
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import MailingAlreadyExists
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserId, UserRole


def _from_model(model: Mailing) -> MailingORM:
    return MailingORM(
        id=model.id,
        status=model.status,
        by_user_id=model.by_user_id,
        body=model.body,
        roles=[r.value for r in model.roles] if model.roles is not None else None,
        total_count=model.total_count,
    )


def _to_model(orm: MailingORM) -> Mailing:
    return Mailing(
        id=MailingId(orm.id),
        status=orm.status,
        by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
        body=orm.body,
        roles=[UserRole(r) for r in orm.roles] if orm.roles is not None else None,
        total_count=orm.total_count,
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
    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self.session = session
        self.uow = uow

    async def add(self, mailing: Mailing) -> None:
        mailing_orm = _from_model(mailing)
        # The ID can come from the client (SendBroadcast), so two overlapping
        # requests with one ID can both pass the interactor's lookup; the
        # second one lands here.
        with translate_integrity_error({"pk_mailings": MailingAlreadyExists}):
            self.session.add(mailing_orm)
            await self.session.flush()
        # Register so any event recorded on the mailing is written to the
        # outbox when the unit of work commits.
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
        stmt = (
            update(MailingORM)
            .where(MailingORM.id == mailing.id)
            .values(
                status=mailing.status,
                body=mailing.body,
                total_count=mailing.total_count,
            )
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
        return int(row.sent_count), int(row.total_count)

    async def read_mailing(self, mailing_id: MailingId) -> MailingDTO | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id)
        mailing_orm = await self.session.scalar(stmt)
        return _parse_dto(mailing_orm) if mailing_orm else None

    async def read_broadcasts(self, pagination: CursorPagination) -> list[MailingDTO]:
        # Organizer broadcasts only: a change announcement has no roles, so it
        # never surfaces in the mailing history. SQLAlchemy writes a Python None
        # into a JSONB column as the JSON value `null`, not SQL NULL, so
        # `roles IS NOT NULL` would match those fan-outs too; test for an array
        # instead. The table is small (manual broadcasts are infrequent), so a
        # plain created_at sort needs no index.
        stmt = (
            select(MailingORM)
            .where(func.jsonb_typeof(MailingORM.roles) == "array")
            # id (uuid7, time-ordered) breaks created_at ties so the page cursor
            # names one row — otherwise same-timestamp rows leave it ambiguous
            # and a mailing slips through unseen.
            .order_by(MailingORM.created_at.desc(), MailingORM.id.desc())
            .limit(pagination.fetch_limit)
        )
        if pagination.after is not None:
            stmt = stmt.where(
                rows_after(MailingORM.created_at, MailingORM.id, pagination.after)
            )
        rows = await self.session.scalars(stmt)
        return [_parse_dto(m) for m in rows]
