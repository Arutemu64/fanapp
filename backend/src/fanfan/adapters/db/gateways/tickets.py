from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import get_constraint_name
from fanfan.adapters.db.mappers.ticket import TicketMapper
from fanfan.adapters.db.models import TicketORM
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.core.exceptions.tickets import UserAlreadyHasTicketLinked
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.user import UserId


class SqlTicketGateway(TicketGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = TicketMapper()

    async def add(self, ticket: Ticket) -> None:
        ticket_orm = self.mapper.from_model(ticket)
        self.session.add(ticket_orm)

    async def get_by_barcode(self, barcode: str) -> Ticket | None:
        stmt = select(TicketORM).where(TicketORM.barcode == barcode).with_for_update()
        ticket_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(ticket_orm) if ticket_orm else None

    async def get_by_ticketscloud_ticket_id(
        self, ticketscloud_ticket_id: str
    ) -> Ticket | None:
        stmt = (
            select(TicketORM)
            .where(TicketORM.ticketscloud_ticket_id == ticketscloud_ticket_id)
            .with_for_update()
        )
        ticket_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(ticket_orm) if ticket_orm else None

    async def get_by_user_id(self, user_id: UserId) -> Ticket | None:
        stmt = (
            select(TicketORM)
            .where(TicketORM.used_by_user_id == user_id)
            .with_for_update()
        )
        ticket_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(ticket_orm) if ticket_orm else None

    async def save(self, ticket: Ticket) -> None:
        try:
            ticket_orm = await self.session.merge(self.mapper.from_model(ticket))
            await self.session.flush([ticket_orm])
        except IntegrityError as e:
            constraint_name = get_constraint_name(e)
            if constraint_name == "uq_tickets_used_by_user_id":
                raise UserAlreadyHasTicketLinked from e
            raise
        return

    async def delete(self, ticket: Ticket) -> None:
        await self.session.execute(delete(TicketORM).where(TicketORM.id == ticket.id))
