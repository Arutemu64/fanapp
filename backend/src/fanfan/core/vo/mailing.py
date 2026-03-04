import enum
from typing import NewType
from uuid import UUID

MailingId = NewType("MailingId", UUID)


class MailingStatus(enum.StrEnum):
    PENDING = "pending"
    FINISHED = "finished"
    CANCELLED = "cancelled"
