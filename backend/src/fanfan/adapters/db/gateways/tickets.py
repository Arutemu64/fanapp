from typing import Any, override

from sqlalchemy import Select, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.constraints import (
    get_constraint_name,
    translate_integrity_error,
)
from fanfan.adapters.db.models import TicketBatchORM, TicketORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.adapters.db.user_ref import parse_user_ref
from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.ticket import TicketListFilter, TicketListItemDTO
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.core.exceptions.tickets import (
    TicketBatchAlreadyExists,
    UserAlreadyHasTicketLinked,
)
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.ticket_batch import TicketBatch
from fanfan.core.vo.ticket import TicketBatchId, TicketId
from fanfan.core.vo.user import UserId

_BARCODE_CONSTRAINT = "uq_tickets_barcode"
_BARCODE_ATTEMPTS = 5


def _from_model(model: Ticket) -> TicketORM:
    return TicketORM(
        id=model.id,
        barcode=model.barcode,
        role=model.role,
        used_by_user_id=model.used_by_user_id,
        issued_by_user_id=model.issued_by_user_id,
        ticketscloud_ticket_id=model.ticketscloud_ticket_id,
        ticketscloud_order_id=model.ticketscloud_order_id,
        revoked_at=model.revoked_at,
        batch_id=model.batch_id,
    )


def _to_model(orm: TicketORM) -> Ticket:
    return Ticket(
        id=TicketId(orm.id),
        barcode=orm.barcode,
        role=orm.role,
        used_by_user_id=UserId(orm.used_by_user_id)
        if orm.used_by_user_id is not None
        else None,
        issued_by_user_id=UserId(orm.issued_by_user_id)
        if orm.issued_by_user_id is not None
        else None,
        ticketscloud_ticket_id=orm.ticketscloud_ticket_id,
        ticketscloud_order_id=orm.ticketscloud_order_id,
        revoked_at=orm.revoked_at,
        batch_id=TicketBatchId(orm.batch_id) if orm.batch_id is not None else None,
    )


def _batch_from_model(model: TicketBatch) -> TicketBatchORM:
    return TicketBatchORM(
        id=model.id,
        role=model.role,
        amount=model.amount,
        issued_by_user_id=model.issued_by_user_id,
    )


def _batch_to_model(orm: TicketBatchORM, tickets: list[TicketORM]) -> TicketBatch:
    return TicketBatch(
        id=TicketBatchId(orm.id),
        role=orm.role,
        amount=orm.amount,
        issued_by_user_id=UserId(orm.issued_by_user_id)
        if orm.issued_by_user_id is not None
        else None,
        tickets=[_to_model(ticket) for ticket in tickets],
    )


def _to_list_item_dto(orm: TicketORM) -> TicketListItemDTO:
    return TicketListItemDTO(
        id=TicketId(orm.id),
        barcode=orm.barcode,
        role=orm.role,
        used_by=parse_user_ref(orm.used_by_user) if orm.used_by_user else None,
        from_ticketscloud=orm.ticketscloud_ticket_id is not None,
        revoked_at=orm.revoked_at,
        created_at=orm.created_at,
    )


class SqlTicketGateway(TicketGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def add(self, ticket: Ticket) -> None:
        ticket_orm = _from_model(ticket)
        self.session.add(ticket_orm)

    @override
    async def add_batch(self, batch: TicketBatch) -> None:
        for attempt in range(1, _BARCODE_ATTEMPTS + 1):
            try:
                await self._insert_batch(batch)
                break
            except IntegrityError as e:
                if get_constraint_name(e) != _BARCODE_CONSTRAINT:
                    raise
                if attempt == _BARCODE_ATTEMPTS:
                    raise
                batch.redraw_barcodes()

    async def _insert_batch(self, batch: TicketBatch) -> None:
        async with self.session.begin_nested():
            with translate_integrity_error(
                {"pk_ticket_batches": TicketBatchAlreadyExists}
            ):
                # No relationship links the two, so flush the batch row first
                # for the tickets' foreign key.
                self.session.add(_batch_from_model(batch))
                await self.session.flush()
                self.session.add_all([_from_model(ticket) for ticket in batch.tickets])
                await self.session.flush()

    @override
    async def get_batch(self, batch_id: TicketBatchId) -> TicketBatch | None:
        batch_orm = await self.session.get(TicketBatchORM, batch_id)
        if batch_orm is None:
            return None
        stmt = (
            select(TicketORM)
            .where(TicketORM.batch_id == batch_id)
            .order_by(TicketORM.id)
        )
        tickets = list(await self.session.scalars(stmt))
        return _batch_to_model(batch_orm, tickets)

    @override
    async def get_by_barcode(self, barcode: str) -> Ticket | None:
        stmt = select(TicketORM).where(TicketORM.barcode == barcode).with_for_update()
        ticket_orm = await self.session.scalar(stmt)
        return _to_model(ticket_orm) if ticket_orm else None

    @override
    async def get_by_ticketscloud_sale(
        self, order_id: str, ticket_id: str
    ) -> Ticket | None:
        stmt = (
            select(TicketORM)
            .where(
                TicketORM.ticketscloud_order_id == order_id,
                TicketORM.ticketscloud_ticket_id == ticket_id,
            )
            .with_for_update()
        )
        ticket_orm = await self.session.scalar(stmt)
        return _to_model(ticket_orm) if ticket_orm else None

    @override
    async def get_legacy_by_ticketscloud_ticket_id(
        self, ticket_id: str
    ) -> Ticket | None:
        stmt = (
            select(TicketORM)
            .where(
                TicketORM.ticketscloud_ticket_id == ticket_id,
                TicketORM.ticketscloud_order_id.is_(None),
            )
            .with_for_update()
        )
        ticket_orm = await self.session.scalar(stmt)
        return _to_model(ticket_orm) if ticket_orm else None

    @override
    async def get_by_user_id(self, user_id: UserId) -> Ticket | None:
        stmt = (
            select(TicketORM)
            .where(TicketORM.used_by_user_id == user_id)
            .with_for_update()
        )
        ticket_orm = await self.session.scalar(stmt)
        return _to_model(ticket_orm) if ticket_orm else None

    @override
    async def save(self, ticket: Ticket) -> None:
        with translate_integrity_error(
            {
                "uq_tickets_used_by_user_id": UserAlreadyHasTicketLinked,
            }
        ):
            await self.session.merge(_from_model(ticket))
            await self.session.flush()

    @override
    async def delete(self, ticket: Ticket) -> None:
        await self.session.execute(delete(TicketORM).where(TicketORM.id == ticket.id))

    @override
    async def read_tickets_page(
        self, *, pagination: CursorPagination, ticket_filter: TicketListFilter
    ) -> list[TicketListItemDTO]:
        stmt = select(TicketORM).options(joinedload(TicketORM.used_by_user))
        stmt = self._apply_ticket_filter(stmt, ticket_filter)
        if pagination.after is not None:
            stmt = stmt.where(
                rows_after(TicketORM.created_at, TicketORM.id, pagination.after)
            )
        stmt = stmt.order_by(TicketORM.created_at.desc(), TicketORM.id.desc()).limit(
            pagination.fetch_limit
        )
        tickets_orm = await self.session.scalars(stmt)
        return [_to_list_item_dto(ticket) for ticket in tickets_orm]

    @override
    async def count_tickets(self, *, ticket_filter: TicketListFilter) -> int:
        stmt = select(func.count(TicketORM.id))
        stmt = self._apply_ticket_filter(stmt, ticket_filter)
        return await self.session.scalar(stmt) or 0

    @staticmethod
    def _apply_ticket_filter[SelectT: Select[Any]](
        stmt: SelectT, ticket_filter: TicketListFilter
    ) -> SelectT:
        search = ticket_filter.search
        if not search or not search.strip():
            return stmt
        escaped = (
            search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        return stmt.where(TicketORM.barcode.ilike(f"%{escaped}%"))
