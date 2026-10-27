from typing import override

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import MailingORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.adapters.db.user_ref import parse_user_ref
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
        created_by=parse_user_ref(orm.by_user) if orm.by_user else None,
        body=orm.body,
        roles=[UserRole(r) for r in orm.roles] if orm.roles is not None else None,
        total_count=orm.total_count,
        created_at=orm.created_at,
    )


class SqlMailingGateway(MailingGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self.session = session
        self.uow = uow

    @override
    async def add(self, mailing: Mailing) -> None:
        mailing_orm = _from_model(mailing)
        with translate_integrity_error({"pk_mailings": MailingAlreadyExists}):
            self.session.add(mailing_orm)
            await self.session.flush()
        self.uow.register(mailing)

    @override
    async def get(self, mailing_id: MailingId, *, lock: bool = True) -> Mailing | None:
        stmt = select(MailingORM).where(MailingORM.id == mailing_id)
        if lock:
            stmt = stmt.with_for_update()
        mailing_orm = await self.session.scalar(stmt)
        if mailing_orm is None:
            return None
        mailing = _to_model(mailing_orm)
        self.uow.register(mailing)
        return mailing

    @override
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

    @override
    async def read_broadcasts(self, pagination: CursorPagination) -> list[MailingDTO]:
        stmt = (
            select(MailingORM)
            .options(joinedload(MailingORM.by_user))
            .where(func.jsonb_typeof(MailingORM.roles) == "array")
            .order_by(MailingORM.created_at.desc(), MailingORM.id.desc())
            .limit(pagination.fetch_limit)
        )
        if pagination.after is not None:
            stmt = stmt.where(
                rows_after(MailingORM.created_at, MailingORM.id, pagination.after)
            )
        rows = await self.session.scalars(stmt)
        return [_parse_dto(m) for m in rows]
