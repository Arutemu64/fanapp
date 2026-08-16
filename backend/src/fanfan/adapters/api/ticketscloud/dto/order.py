from dataclasses import dataclass
from enum import StrEnum

from fanfan.adapters.api.ticketscloud.dto.pagination import Pagination
from fanfan.adapters.api.ticketscloud.dto.ticket import Ticket


class OrderStatus(StrEnum):
    EXECUTED = "executed"
    DONE = "done"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    IN_PROGRESS = "in_progress"


@dataclass(slots=True, frozen=True)
class Order:
    id: str
    status: OrderStatus
    event: str
    tickets: list[Ticket]


@dataclass(slots=True, frozen=True)
class OrderResponse:
    # The single-order endpoint wraps the order in the same `data` envelope the
    # list endpoint uses, just without pagination — so the order fields live
    # under `data`, not at the top level.
    data: Order


@dataclass(slots=True, frozen=True)
class OrdersResponse:
    data: list[Order]
    pagination: Pagination
    total_count: int
