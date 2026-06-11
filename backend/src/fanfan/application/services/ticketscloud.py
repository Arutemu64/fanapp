import logging

from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.api.ticketscloud.dto.order import Order, OrderStatus
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import generate_ticket_id
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class TCloudService:
    def __init__(
        self,
        config: TCloudConfig,
        ticket_gateway: TicketGateway,
    ):
        self.config = config
        self.ticket_gateway = ticket_gateway

    async def proceed_order(self, order: Order) -> int:
        # TODO Handle revocation. This only ever adds tickets for DONE orders;
        # CANCELLED / EXPIRED / refunded orders are ignored, so a ticket issued
        # and later cancelled upstream stays valid forever. Revoke (delete or
        # flag) the matching ticket when the order is no longer DONE, and wire
        # up removed_tickets_count in SyncTCloud once refunds are handled.
        new_tickets_count = 0
        for order_ticket in order.tickets:
            ticket = await self.ticket_gateway.get_by_ticketscloud_ticket_id(
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
                await self.ticket_gateway.add(ticket)
                logger.info(
                    "New ticket %s was added", ticket.id, extra={"ticket": ticket}
                )
                new_tickets_count += 1
        return new_tickets_count
