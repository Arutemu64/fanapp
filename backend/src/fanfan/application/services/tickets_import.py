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
    barcode. Rows imported before the order id was stored match by ticket id
    alone until a sync fills their order id in.
    """

    def __init__(self, ticket_gateway: TicketGateway) -> None:
        self.ticket_gateway = ticket_gateway

    async def import_ticket(self, external: ExternalTicket) -> bool:
        existing = await self.ticket_gateway.get_by_ticketscloud_sale(
            order_id=external.order_id, ticket_id=external.external_id
        )
        if existing is not None:
            return False

        legacy = await self.ticket_gateway.get_by_barcode(external.barcode)
        if legacy is not None:
            if (
                legacy.ticketscloud_order_id is None
                and legacy.ticketscloud_ticket_id == external.external_id
            ):
                legacy.ticketscloud_order_id = external.order_id
                await self.ticket_gateway.save(legacy)
            else:
                logger.warning(
                    "Imported barcode already belongs to another ticket",
                    extra={"ticket_id": str(legacy.id)},
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
        await self.ticket_gateway.add(ticket)
        logger.info("New ticket added", extra={"ticket_id": str(ticket.id)})
        return True

    async def revoke_ticket(self, revoked: RevokedExternalTicket) -> bool:
        ticket = await self.ticket_gateway.get_by_ticketscloud_sale(
            order_id=revoked.order_id, ticket_id=revoked.external_id
        )
        if ticket is None:
            # Safe for a row with no order id: before the order id was stored, a
            # resale of the same ticket id was never imported, so that row is
            # the only sale of this ticket id we hold, and any refund of the id
            # implies that sale was refunded first.
            ticket = await self.ticket_gateway.get_legacy_by_ticketscloud_ticket_id(
                revoked.external_id
            )
        if ticket is None or ticket.is_revoked:
            return False

        ticket.revoke(datetime.now(UTC))
        await self.ticket_gateway.save(ticket)
        logger.info("Ticket revoked", extra={"ticket_id": str(ticket.id)})
        return True
