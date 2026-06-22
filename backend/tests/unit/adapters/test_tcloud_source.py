import pytest
from pydantic import SecretStr

from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.api.ticketscloud.dto.order import (
    Order,
    OrdersResponse,
    OrderStatus,
)
from fanfan.adapters.api.ticketscloud.dto.pagination import Pagination
from fanfan.adapters.api.ticketscloud.dto.ticket import Ticket
from fanfan.adapters.api.ticketscloud.source import TCloudSource
from fanfan.core.vo.user import UserRole

pytestmark = pytest.mark.unit

EVENT_HELPER = "event-helper"
EVENT_UNKNOWN = "event-unknown"


def _ticket(ticket_id: str, *, barcode: str | None) -> Ticket:
    return Ticket(
        id=ticket_id,
        serial="S",
        number=1,
        barcode=barcode,
        status="ok",
        price="0",
        nominal="0",
        discount="0",
        extra="",
        full="",
        set="",
        tariff=None,
    )


def _order(
    order_id: str,
    *,
    status: OrderStatus = OrderStatus.DONE,
    event: str = EVENT_HELPER,
    tickets: list[Ticket],
) -> Order:
    return Order(id=order_id, status=status, event=event, tickets=tickets)


def _config() -> TCloudConfig:
    return TCloudConfig(
        api_key=SecretStr("key"),
        event_ids_map={EVENT_HELPER: UserRole.HELPER},
    )


class FakeTCloudClient:
    """Stands in for TCloudClient, returning canned orders (no HTTP)."""

    def __init__(
        self, pages: list[list[Order]], orders_by_id: dict[str, Order] | None = None
    ) -> None:
        self._pages = pages
        self._orders_by_id = orders_by_id or {}

    async def get_orders(self, page: int = 1, page_size: int = 200) -> OrdersResponse:
        data = self._pages[page - 1]
        return OrdersResponse(
            data=data,
            pagination=Pagination(
                page=page, page_size=page_size, total=len(self._pages)
            ),
            total_count=sum(len(p) for p in self._pages),
        )

    async def get_order(self, order_id: str) -> Order | None:
        return self._orders_by_id.get(order_id)


async def test_fetch_order_tickets_filters_and_maps_role() -> None:
    order = _order(
        "o1",
        tickets=[
            _ticket("t1", barcode="B1"),  # kept
            _ticket("t2", barcode=None),  # no barcode -> dropped
        ],
    )
    source = TCloudSource(
        FakeTCloudClient(pages=[[]], orders_by_id={"o1": order}), _config()
    )

    tickets = await source.fetch_order_tickets("o1")

    assert len(tickets) == 1
    assert tickets[0].external_id == "t1"
    assert tickets[0].barcode == "B1"
    assert tickets[0].role is UserRole.HELPER


async def test_fetch_order_tickets_skips_non_done_order() -> None:
    order = _order(
        "o1", status=OrderStatus.CANCELLED, tickets=[_ticket("t1", barcode="B1")]
    )
    source = TCloudSource(
        FakeTCloudClient(pages=[[]], orders_by_id={"o1": order}), _config()
    )

    assert await source.fetch_order_tickets("o1") == []


async def test_fetch_order_tickets_missing_order_returns_empty() -> None:
    source = TCloudSource(FakeTCloudClient(pages=[[]]), _config())

    assert await source.fetch_order_tickets("nope") == []


async def test_unmapped_event_falls_back_to_visitor() -> None:
    order = _order("o1", event=EVENT_UNKNOWN, tickets=[_ticket("t1", barcode="B1")])
    source = TCloudSource(
        FakeTCloudClient(pages=[[]], orders_by_id={"o1": order}), _config()
    )

    tickets = await source.fetch_order_tickets("o1")

    assert tickets[0].role is UserRole.VISITOR


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
    source = TCloudSource(FakeTCloudClient(pages=pages), _config())

    collected = [ticket async for ticket in source.fetch_all_tickets()]

    # t3 dropped (order not DONE); t1 and t2 streamed across both pages.
    assert [t.external_id for t in collected] == ["t1", "t2"]
