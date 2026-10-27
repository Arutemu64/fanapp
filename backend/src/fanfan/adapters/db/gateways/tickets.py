from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import TicketORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.adapters.db.user_ref import parse_user_ref
from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.ticket import TicketListFilter, TicketListItemDTO
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.core.exceptions.tickets import (
    TicketBarcodeCollision,
    UserAlreadyHasTicketLinked,
)
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId


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

    async def add(self, ticket: Ticket) -> None:
        ticket_orm = _from_model(ticket)
        self.session.add(ticket_orm)

    async def add_all(self, tickets: list[Ticket]) -> None:
        ticket_orms = [_from_model(ticket) for ticket in tickets]
        self.session.add_all(ticket_orms)
        with translate_integrity_error({"uq_tickets_barcode": TicketBarcodeCollision}):
            await self.session.flush()

    async def get_by_barcode(self, barcode: str) -> Ticket | None:
        stmt = select(TicketORM).where(TicketORM.barcode == barcode).with_for_update()
        ticket_orm = await self.session.scalar(stmt)
        return _to_model(ticket_orm) if ticket_orm else None

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

    async def get_by_user_id(self, user_id: UserId) -> Ticket | None:
        stmt = (
            select(TicketORM)
            .where(TicketORM.used_by_user_id == user_id)
            .with_for_update()
        )
        ticket_orm = await self.session.scalar(stmt)
        return _to_model(ticket_orm) if ticket_orm else None

    async def save(self, ticket: Ticket) -> None:
        with translate_integrity_error(
            {
                "uq_tickets_used_by_user_id": UserAlreadyHasTicketLinked,
            }
        ):
            await self.session.merge(_from_model(ticket))
            await self.session.flush()

    async def delete(self, ticket: Ticket) -> None:
        await self.session.execute(delete(TicketORM).where(TicketORM.id == ticket.id))

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
