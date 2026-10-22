from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class ExternalTicket:
    # The source reuses a ticket id when a refunded ticket is sold again, so the
    # idempotency key is the sale: order_id together with external_id.
    order_id: str
    external_id: str
    barcode: str
    # The vendor event the ticket was sold for. The role it grants is the
    # organizer's call (AppSettings.tickets), so it is resolved on import rather
    # than here.
    event_id: str


@dataclass(slots=True, frozen=True)
class RevokedExternalTicket:
    order_id: str
    external_id: str


class TicketsSource(Protocol):
    """Read port into the external ticketing platform (TicketsCloud).

    Yields only valid, purchasable tickets; vendor order/status concepts never
    cross this boundary.
    """

    def fetch_all_tickets(self) -> AsyncIterator[ExternalTicket]: ...
    async def fetch_order_tickets(self, order_id: str) -> list[ExternalTicket]: ...
    def fetch_revoked_tickets(self) -> AsyncIterator[RevokedExternalTicket]: ...
