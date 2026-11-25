from enum import StrEnum

from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.dto.pagination import Pagination
from fanfan.adapters.api.ticketscloud.dto.ticket import Ticket


class OrderStatus(StrEnum):
    EXECUTED = "executed"
    DONE = "done"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    IN_PROGRESS = "in_progress"


class Order(BaseModel, frozen=True):
    id: str
    status: OrderStatus
    event: str
    tickets: list[Ticket]


class OrderResponse(BaseModel, frozen=True):
    data: Order


class OrdersResponse(BaseModel, frozen=True):
    data: list[Order]
    pagination: Pagination
