import enum
from dataclasses import dataclass

from fanfan.core.vo.participant import ValueType


class RequestStatus(enum.StrEnum):
    PENDING = "pending"  # Under review
    WAITING = "waiting"  # Response needed
    MATERIALS = "materials"  # Awaiting materials
    REVIEW = "review"  # Reviewed
    APPROVED = "approved"  # Accepted
    DISAPPROVED = "disapproved"  # Rejected


@dataclass(slots=True, frozen=True)
class Request:
    id: int
    topic_id: int
    voting_number: int | None
    voting_title: str | None
    status: RequestStatus


@dataclass(slots=True, frozen=True)
class RequestValueDTO:
    request_id: int
    title: str
    type: ValueType
    value: str | None
