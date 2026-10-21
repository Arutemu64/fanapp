import logging
from datetime import UTC, datetime

from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.sources.tickets import (
    ExternalTicket,
    RevokedExternalTicket,
)
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import generate_ticket_id

logger = logging.getLogger(__name__)


class TicketImportService:
    """Persists tickets coming from an external source, idempotently.

    Vendor-neutral: it consumes the application's ExternalTicket DTO, so it has
    no knowledge of how the tickets were fetched or translated.

    A sale is keyed by (order id, ticket id): the source sells a refunded ticket
    id again under a new order, and that resale is a new ticket with its own
    barcode.
    """

    def __init__(self, ticket_gateway: TicketGateway) -> None:
        self.ticket_gateway = ticket_gateway

    async def import_ticket(
        self, external: ExternalTicket, *, refunded: bool = False
    ) -> bool:
        existing = await self.ticket_gateway.get_by_ticketscloud_sale(
            order_id=external.order_id, ticket_id=external.external_id
        )
        if existing is not None:
            return False

        clashing = await self.ticket_gateway.get_by_barcode(external.barcode)
        if clashing is not None:
            logger.warning(
                "Imported barcode already belongs to another ticket",
                extra={"ticket_id": str(clashing.id)},
            )
            return False

        ticket = Ticket(
            id=generate_ticket_id(),
            barcode=external.barcode,
            role=external.role,
            used_by_user_id=None,
            issued_by_user_id=None,
            ticketscloud_ticket_id=external.external_id,
            ticketscloud_order_id=external.order_id,
        )
        if refunded:
            ticket.revoke(datetime.now(UTC))
        await self.ticket_gateway.add(ticket)
        logger.info("New ticket added", extra={"ticket_id": str(ticket.id)})
        return True

    async def revoke_ticket(self, revoked: RevokedExternalTicket) -> bool:
        ticket = await self.ticket_gateway.get_by_ticketscloud_sale(
            order_id=revoked.order_id, ticket_id=revoked.external_id
        )
        if ticket is None or ticket.is_revoked:
            return False

        ticket.revoke(datetime.now(UTC))
        await self.ticket_gateway.save(ticket)
        logger.info("Ticket revoked", extra={"ticket_id": str(ticket.id)})
        return True
