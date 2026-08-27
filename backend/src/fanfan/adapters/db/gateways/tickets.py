from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import TicketORM
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
    )


class SqlTicketGateway(TicketGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, ticket: Ticket) -> None:
        ticket_orm = _from_model(ticket)
        self.session.add(ticket_orm)

    async def add_all(self, tickets: list[Ticket]) -> None:
        ticket_orms = [_from_model(ticket) for ticket in tickets]
        self.session.add_all(ticket_orms)
        # Flush here so a duplicate barcode surfaces as a domain exception at the
        # gateway (not later at uow.commit()); the caller regenerates and retries.
        with translate_integrity_error({"uq_tickets_barcode": TicketBarcodeCollision}):
            await self.session.flush(ticket_orms)

    async def get_by_barcode(self, barcode: str) -> Ticket | None:
        stmt = select(TicketORM).where(TicketORM.barcode == barcode).with_for_update()
        ticket_orm = await self.session.scalar(stmt)
        return _to_model(ticket_orm) if ticket_orm else None

    async def get_by_ticketscloud_ticket_id(
        self, ticketscloud_ticket_id: str
    ) -> Ticket | None:
        stmt = (
            select(TicketORM)
            .where(TicketORM.ticketscloud_ticket_id == ticketscloud_ticket_id)
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
            ticket_orm = await self.session.merge(_from_model(ticket))
            await self.session.flush([ticket_orm])

    async def delete(self, ticket: Ticket) -> None:
        await self.session.execute(delete(TicketORM).where(TicketORM.id == ticket.id))
