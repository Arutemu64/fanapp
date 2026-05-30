import enum
from typing import NewType
from uuid import UUID, uuid7

MailingId = NewType("MailingId", UUID)


def generate_mailing_id() -> MailingId:
    return MailingId(uuid7())


class MailingStatus(enum.StrEnum):
    PENDING = "pending"
    FINISHED = "finished"
    CANCELLED = "cancelled"
