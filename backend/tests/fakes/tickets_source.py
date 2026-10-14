from collections.abc import AsyncIterator

from fanfan.application.ports.sources.tickets import (
    ExternalTicket,
    RevokedExternalTicket,
    TicketsSource,
)


class FakeTicketsSource(TicketsSource):
    """In-memory TicketsSource replacing the TicketsCloud HTTP client in tests.

    A test assigns the tickets a full sync should yield (``tickets``), the
    refunded sales it should revoke (``revoked``) and the per-order tickets a
    webhook flow should see (``order_tickets``); the fake
    records which order ids were fetched so callers can assert on it.
    """

    def __init__(self) -> None:
        self.tickets: list[ExternalTicket] = []
        self.revoked: list[RevokedExternalTicket] = []
        self.order_tickets: dict[str, list[ExternalTicket]] = {}
        self.fetched_order_ids: list[str] = []

    def fetch_all_tickets(self) -> AsyncIterator[ExternalTicket]:
        return self._iter_tickets()

    async def _iter_tickets(self) -> AsyncIterator[ExternalTicket]:
        for ticket in self.tickets:
            yield ticket

    def fetch_revoked_tickets(self) -> AsyncIterator[RevokedExternalTicket]:
        return self._iter_revoked()

    async def _iter_revoked(self) -> AsyncIterator[RevokedExternalTicket]:
        for revoked in self.revoked:
            yield revoked

    async def fetch_order_tickets(self, order_id: str) -> list[ExternalTicket]:
        self.fetched_order_ids.append(order_id)
        return self.order_tickets.get(order_id, [])
