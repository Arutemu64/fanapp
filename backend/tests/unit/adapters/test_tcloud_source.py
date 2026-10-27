from typing import override

import pytest

from fanfan.adapters.api.ticketscloud.client import TCloudClient
from fanfan.adapters.api.ticketscloud.dto.order import (
    Order,
    OrdersResponse,
    OrderStatus,
)
from fanfan.adapters.api.ticketscloud.dto.pagination import Pagination
from fanfan.adapters.api.ticketscloud.dto.refund import (
    Refund,
    RefundsResponse,
    RefundStatus,
)
from fanfan.adapters.api.ticketscloud.dto.ticket import Ticket
from fanfan.adapters.api.ticketscloud.source import TCloudSource
from fanfan.application.ports.sources.tickets import RevokedExternalTicket

pytestmark = pytest.mark.unit

EVENT_VOLUNTEER = "event-volunteer"


def _ticket(ticket_id: str, *, barcode: str | None) -> Ticket:
    return Ticket(id=ticket_id, barcode=barcode)


def _order(
    order_id: str,
    *,
    status: OrderStatus = OrderStatus.DONE,
    event: str = EVENT_VOLUNTEER,
    tickets: list[Ticket],
) -> Order:
    return Order(id=order_id, status=status, event=event, tickets=tickets)


class FakeTCloudClient(TCloudClient):
    """Stands in for TCloudClient, returning canned orders (no HTTP).

    Subclasses the real client so `ty` verifies these signatures against the
    ones the source calls. `__init__` does not call super(): there is no httpx
    pool or retort here, and the overrides replace every use of them.
    """

    def __init__(
        self,
        pages: list[list[Order]],
        orders_by_id: dict[str, Order] | None = None,
        refund_pages: list[list[Refund]] | None = None,
    ) -> None:
        self._pages = pages
        self._orders_by_id = orders_by_id or {}
        self._refund_pages = refund_pages or [[]]
        self.order_statuses: list[OrderStatus] = []
        self.refund_statuses: list[RefundStatus] = []

    @override
    async def get_orders(
        self, status: OrderStatus, page: int = 1, page_size: int = 200
    ) -> OrdersResponse:
        self.order_statuses.append(status)
        data = self._pages[page - 1]
        return OrdersResponse(
            data=data,
            pagination=Pagination(
                page=page, page_size=page_size, total=len(self._pages)
            ),
        )

    @override
    async def get_order(self, order_id: str) -> Order | None:
        return self._orders_by_id.get(order_id)

    @override
    async def get_refunds(
        self, status: RefundStatus, page: int = 1, page_size: int = 200
    ) -> RefundsResponse:
        self.refund_statuses.append(status)
        return RefundsResponse(
            data=self._refund_pages[page - 1],
            pagination=Pagination(
                page=page, page_size=page_size, total=len(self._refund_pages)
            ),
        )


async def test_fetch_order_tickets_filters_and_keeps_event() -> None:
    order = _order(
        "o1",
        tickets=[
            _ticket("t1", barcode="B1"),
            _ticket("t2", barcode=None),
        ],
    )
    source = TCloudSource(FakeTCloudClient(pages=[[]], orders_by_id={"o1": order}))

    tickets = await source.fetch_order_tickets("o1")

    assert len(tickets) == 1
    assert tickets[0].order_id == "o1"
    assert tickets[0].external_id == "t1"
    assert tickets[0].barcode == "B1"
    assert tickets[0].event_id == EVENT_VOLUNTEER


async def test_fetch_order_tickets_skips_non_done_order() -> None:
    order = _order(
        "o1", status=OrderStatus.CANCELLED, tickets=[_ticket("t1", barcode="B1")]
    )
    source = TCloudSource(FakeTCloudClient(pages=[[]], orders_by_id={"o1": order}))

    assert await source.fetch_order_tickets("o1") == []


async def test_fetch_order_tickets_missing_order_returns_empty() -> None:
    source = TCloudSource(FakeTCloudClient(pages=[[]]))

    assert await source.fetch_order_tickets("nope") == []


async def test_fetch_all_tickets_paginates_and_streams() -> None:
    pages = [
        [_order("o1", tickets=[_ticket("t1", barcode="B1")])],
        [
            _order("o2", tickets=[_ticket("t2", barcode="B2")]),
            _order(
                "o3", status=OrderStatus.EXPIRED, tickets=[_ticket("t3", barcode="B3")]
            ),
        ],
    ]
    client = FakeTCloudClient(pages=pages)
    source = TCloudSource(client)

    collected = [ticket async for ticket in source.fetch_all_tickets()]

    assert [t.external_id for t in collected] == ["t1", "t2"]
    assert client.order_statuses == [OrderStatus.DONE, OrderStatus.DONE]


async def test_fetch_revoked_tickets_reads_every_approved_refund_page() -> None:
    def refund(refund_id: str, order_id: str, tickets: list[str]) -> Refund:
        return Refund(id=refund_id, order=order_id, tickets=tickets)

    client = FakeTCloudClient(
        pages=[[]],
        refund_pages=[
            [refund("r1", "o1", ["t1", "t2"])],
            [refund("r2", "o2", ["t3"])],
        ],
    )
    source = TCloudSource(client)

    revoked = [ticket async for ticket in source.fetch_revoked_tickets()]

    assert revoked == [
        RevokedExternalTicket(order_id="o1", external_id="t1"),
        RevokedExternalTicket(order_id="o1", external_id="t2"),
        RevokedExternalTicket(order_id="o2", external_id="t3"),
    ]
    assert client.refund_statuses == [RefundStatus.APPROVED, RefundStatus.APPROVED]
