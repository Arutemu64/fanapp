from dataclasses import dataclass
from enum import StrEnum

from fanfan.adapters.api.ticketscloud.dto.pagination import Pagination


class RefundStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(slots=True, frozen=True)
class Refund:
    id: str
    order: str
    tickets: list[str]  # list of ticket ids


@dataclass(slots=True, frozen=True)
class RefundsResponse:
    data: list[Refund]
    pagination: Pagination
