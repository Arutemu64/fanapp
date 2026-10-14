from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from fanfan.core.vo.user import UserRole


@dataclass(slots=True, frozen=True)
class ExternalTicket:
    # The source reuses a ticket id when a refunded ticket is sold again, so the
    # idempotency key is the sale: order_id together with external_id.
    order_id: str
    external_id: str
    barcode: str
    role: UserRole


@dataclass(slots=True, frozen=True)
class RevokedExternalTicket:
    order_id: str
    external_id: str


class TicketsSource(Protocol):
    """Read port into the external ticketing platform (TicketsCloud).

    Yields only valid, purchasable tickets already resolved to a domain role;
    vendor order/status concepts never cross this boundary.
    """

    def fetch_all_tickets(self) -> AsyncIterator[ExternalTicket]: ...
    async def fetch_order_tickets(self, order_id: str) -> list[ExternalTicket]: ...
    def fetch_revoked_tickets(self) -> AsyncIterator[RevokedExternalTicket]: ...
