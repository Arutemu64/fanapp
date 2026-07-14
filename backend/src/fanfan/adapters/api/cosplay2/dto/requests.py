import enum
from dataclasses import dataclass


class RequestStatus(enum.StrEnum):
    # Comments show the label as displayed on the cosplay2 site (in Russian).
    PENDING = "pending"  # Under review ("Проверка")
    WAITING = "waiting"  # Response needed ("Нужен отклик")
    MATERIALS = "materials"  # Awaiting materials ("Ждём материалы")
    REVIEW = "review"  # Reviewed ("Рассмотрена")
    APPROVED = "approved"  # Accepted ("Принята")
    DISAPPROVED = "disapproved"  # Rejected ("Отклонена")


@dataclass(slots=True, frozen=True)
class Request:
    id: int
    topic_id: int
    voting_number: int | None
    voting_title: str | None
    status: RequestStatus
