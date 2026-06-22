import logging
from collections.abc import AsyncIterator, Iterator

from fanfan.adapters.api.ticketscloud.client import TCloudClient
from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.api.ticketscloud.dto.order import Order, OrderStatus
from fanfan.application.ports.sources.tickets import ExternalTicket, TicketsSource
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 200


class TCloudSource(TicketsSource):
    """Anti-corruption layer over the TicketsCloud HTTP client.

    Interprets vendor orders into the neutral tickets the application stores:
    only DONE orders with a barcode yield a ticket, and the vendor event id is
    mapped to a domain role here so the boundary speaks the domain's language.
    """

    def __init__(self, client: TCloudClient, config: TCloudConfig):
        self.client = client
        self.config = config

    def _extract_tickets(self, order: Order) -> Iterator[ExternalTicket]:
        if order.status != OrderStatus.DONE:
            return
        role = self.config.event_ids_map.get(order.event, UserRole.VISITOR)
        for order_ticket in order.tickets:
            if order_ticket.barcode:
                yield ExternalTicket(
                    external_id=order_ticket.id,
                    barcode=order_ticket.barcode,
                    role=role,
                )

    def fetch_all_tickets(self) -> AsyncIterator[ExternalTicket]:
        async def iterator() -> AsyncIterator[ExternalTicket]:
            # Reuse the first page to read the total page count, then request
            # the rest starting from page 2 so page 1 is not fetched twice.
            first_page = await self.client.get_orders(
                page=1, page_size=DEFAULT_PAGE_SIZE
            )
            logger.info(
                "TicketsCloud sync started",
                extra={"order_count": first_page.total_count},
            )
            for page in range(1, first_page.pagination.total + 1):
                result = (
                    first_page
                    if page == 1
                    else await self.client.get_orders(
                        page=page, page_size=DEFAULT_PAGE_SIZE
                    )
                )
                for order in result.data:
                    for ticket in self._extract_tickets(order):
                        yield ticket

        return iterator()

    async def fetch_order_tickets(self, order_id: str) -> list[ExternalTicket]:
        # The order id comes from an untrusted webhook body, so the authoritative
        # order is fetched from the authenticated API. A missing order yields no
        # tickets rather than an error.
        order = await self.client.get_order(order_id)
        if order is None:
            logger.warning(
                "TicketsCloud order not found, ignoring",
                extra={"order_id": order_id},
            )
            return []
        return list(self._extract_tickets(order))
