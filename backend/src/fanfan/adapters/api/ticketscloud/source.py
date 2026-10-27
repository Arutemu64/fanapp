import logging
from collections.abc import AsyncIterator, Iterator
from typing import override

from fanfan.adapters.api.ticketscloud.client import TCloudClient
from fanfan.adapters.api.ticketscloud.dto.order import Order, OrderStatus
from fanfan.adapters.api.ticketscloud.dto.refund import RefundStatus
from fanfan.application.ports.sources.tickets import (
    ExternalTicket,
    RevokedExternalTicket,
    TicketsSource,
)

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 200


def _extract_tickets(order: Order) -> Iterator[ExternalTicket]:
    if order.status != OrderStatus.DONE:
        return
    for order_ticket in order.tickets:
        if order_ticket.barcode:
            yield ExternalTicket(
                order_id=order.id,
                external_id=order_ticket.id,
                barcode=order_ticket.barcode,
                event_id=order.event,
            )


class TCloudSource(TicketsSource):
    """Anti-corruption layer over the TicketsCloud HTTP client.

    Interprets vendor orders into the neutral tickets the application stores:
    only DONE orders with a barcode yield a ticket, and an approved refund
    request is what revokes a sold ticket. The vendor event id passes through
    as is: which role it grants is organizer data, kept in AppSettings.
    """

    def __init__(self, client: TCloudClient) -> None:
        self.client = client

    @override
    def fetch_all_tickets(self) -> AsyncIterator[ExternalTicket]:
        async def iterator() -> AsyncIterator[ExternalTicket]:
            first_page = await self.client.get_orders(
                status=OrderStatus.DONE, page=1, page_size=DEFAULT_PAGE_SIZE
            )
            logger.info(
                "TicketsCloud sync started",
                extra={"page_count": first_page.pagination.total},
            )
            for page in range(1, first_page.pagination.total + 1):
                result = first_page
                if page > 1:
                    result = await self.client.get_orders(
                        status=OrderStatus.DONE,
                        page=page,
                        page_size=DEFAULT_PAGE_SIZE,
                    )
                for order in result.data:
                    for ticket in _extract_tickets(order):
                        yield ticket

        return iterator()

    @override
    def fetch_revoked_tickets(self) -> AsyncIterator[RevokedExternalTicket]:
        async def iterator() -> AsyncIterator[RevokedExternalTicket]:
            page = 1
            total_pages = 1
            while page <= total_pages:
                result = await self.client.get_refunds(
                    status=RefundStatus.APPROVED,
                    page=page,
                    page_size=DEFAULT_PAGE_SIZE,
                )
                total_pages = result.pagination.total
                for refund in result.data:
                    for ticket_id in refund.tickets:
                        yield RevokedExternalTicket(
                            order_id=refund.order, external_id=ticket_id
                        )
                page += 1

        return iterator()

    @override
    async def fetch_order_tickets(self, order_id: str) -> list[ExternalTicket]:
        order = await self.client.get_order(order_id)
        if order is None:
            logger.warning(
                "TicketsCloud order not found, ignoring",
                extra={"order_id": order_id},
            )
            return []
        return list(_extract_tickets(order))
