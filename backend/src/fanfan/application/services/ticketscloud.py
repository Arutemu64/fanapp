import logging

from fanfan.adapters.api.ticketscloud.client import TCloudClient
from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.api.ticketscloud.dto.order import Order, OrderStatus
from fanfan.adapters.api.ticketscloud.dto.refund import Refund, RefundStatus
from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.services.tickets import TicketService
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import generate_ticket_id
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class TCloudService:
    def __init__(
        self,
        config: TCloudConfig,
        client: TCloudClient,
        ticket_repo: TicketRepository,
        ticket_service: TicketService,
    ):
        self.config = config
        self.client = client
        self.ticket_repo = ticket_repo
        self.ticket_service = ticket_service

    async def proceed_order(self, order: Order) -> int:
        new_tickets_count = 0
        for order_ticket in order.tickets:
            ticket = await self.ticket_repo.get_by_ticketscloud_ticket_id(
                order_ticket.id
            )
            if (
                order.status == OrderStatus.DONE
                and ticket is None
                and order_ticket.barcode
            ):
                role = self.config.event_ids_map.get(order.event, UserRole.VISITOR)
                ticket = Ticket(
                    id=generate_ticket_id(),
                    barcode=order_ticket.barcode,
                    role=role,
                    used_by_user_id=None,
                    issued_by_user_id=None,
                    ticketscloud_ticket_id=order_ticket.id,
                )
                await self.ticket_repo.add(ticket)
                logger.info(
                    "New ticket %s was added", ticket.id, extra={"ticket": ticket}
                )
                new_tickets_count += 1
        return new_tickets_count

    async def proceed_refund(self, refund: Refund) -> int:
        removed_tickets_count = 0
        for ticket_id in refund.tickets:
            ticket = await self.ticket_repo.get_by_ticketscloud_ticket_id(ticket_id)
            if refund.status == RefundStatus.APPROVED and ticket:
                await self.ticket_service.unlink_ticket(ticket)
                await self.ticket_repo.delete(ticket)
                logger.info(
                    "Ticket %s was refunded", ticket.id, extra={"ticket": ticket}
                )
                removed_tickets_count += 1
        return removed_tickets_count
