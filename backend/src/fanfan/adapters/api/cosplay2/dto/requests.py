import enum
from dataclasses import dataclass


class RequestStatus(enum.StrEnum):
    PENDING = "pending"
    WAITING = "waiting"
    MATERIALS = "materials"
    REVIEW = "review"
    APPROVED = "approved"
    DISAPPROVED = "disapproved"


@dataclass(slots=True, frozen=True)
class Request:
    id: int
    topic_id: int
    voting_number: int | None
    voting_title: str | None
    status: RequestStatus
