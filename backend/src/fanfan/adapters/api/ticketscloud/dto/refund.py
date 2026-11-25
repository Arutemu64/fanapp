from enum import StrEnum

from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.dto.pagination import Pagination


class RefundStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


class Refund(BaseModel, frozen=True):
    id: str
    order: str
    tickets: list[str]


class RefundsResponse(BaseModel, frozen=True):
    data: list[Refund]
    pagination: Pagination
