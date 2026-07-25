import logging

from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.sources.tickets import ExternalTicket
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import generate_ticket_id

logger = logging.getLogger(__name__)


class TicketImportService:
    """Persists tickets coming from an external source, idempotently.

    Vendor-neutral: it consumes the application's ExternalTicket DTO, so it has
    no knowledge of how the tickets were fetched or translated.
    """

    def __init__(self, ticket_gateway: TicketGateway):
        self.ticket_gateway = ticket_gateway

    async def import_ticket(self, external: ExternalTicket) -> bool:
        # TODO: Handle revocation by deleting the matching ticket when an order
        # is no longer DONE (CANCELLED / EXPIRED / refunded). NOT implemented
        # yet: TicketsCloud reuses ticket ids — a revoked ticket can be resold
        # under the same id, so naive deletion would drop a now-valid ticket.
        # Any revocation must key off more than the external id (e.g. also the
        # barcode/serial) before it is safe.
        existing = await self.ticket_gateway.get_by_ticketscloud_ticket_id(
            external.external_id
        )
        if existing is not None:
            return False
        ticket = Ticket(
            id=generate_ticket_id(),
            barcode=external.barcode,
            role=external.role,
            used_by_user_id=None,
            issued_by_user_id=None,
            ticketscloud_ticket_id=external.external_id,
        )
        await self.ticket_gateway.add(ticket)
        logger.info("New ticket %s was added", ticket.id, extra={"ticket": ticket})
        return True
