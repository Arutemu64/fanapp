from pydantic import BaseModel

from fanfan.application.dto.page import CursorPagination, cut_page
from fanfan.application.dto.ticket import TicketListFilter, TicketListItemDTO
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class ListTicketsInput(BaseModel):
    pagination: CursorPagination
    ticket_filter: TicketListFilter = TicketListFilter()


class ListTicketsOutput(BaseModel):
    tickets: list[TicketListItemDTO]
    total: int
    next_cursor: str | None


class ListTickets:
    """Newest-first list of every ticket, generated or imported, for organizers."""

    def __init__(
        self,
        ticket_gateway: TicketGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.ticket_gateway = ticket_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self, data: ListTicketsInput) -> ListTicketsOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.TICKETS_MANAGE
        )

        rows = await self.ticket_gateway.read_tickets_page(
            pagination=data.pagination, ticket_filter=data.ticket_filter
        )
        tickets, next_cursor = cut_page(rows, data.pagination)
        total = await self.ticket_gateway.count_tickets(
            ticket_filter=data.ticket_filter
        )
        return ListTicketsOutput(tickets=tickets, total=total, next_cursor=next_cursor)
