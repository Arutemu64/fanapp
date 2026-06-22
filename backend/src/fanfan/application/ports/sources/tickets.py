from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from fanfan.core.vo.user import UserRole


@dataclass(slots=True, frozen=True)
class ExternalTicket:
    # external_id is the source ticket id, used as the idempotency key; the
    # interactor stores it on the domain ticket's `ticketscloud_ticket_id` field.
    external_id: str
    barcode: str
    role: UserRole


class TicketsSource(Protocol):
    """Read port into the external ticketing platform (TicketsCloud).

    Yields only valid, purchasable tickets already resolved to a domain role;
    vendor order/status concepts never cross this boundary.
    """

    def fetch_all_tickets(self) -> AsyncIterator[ExternalTicket]: ...
    async def fetch_order_tickets(self, order_id: str) -> list[ExternalTicket]: ...
