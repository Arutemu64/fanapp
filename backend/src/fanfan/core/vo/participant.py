import enum
from typing import NewType
from uuid import UUID, uuid7

ParticipantId = NewType("ParticipantId", UUID)


def generate_participant_id() -> ParticipantId:
    return ParticipantId(uuid7())


class ValueType(enum.StrEnum):
    TEXT = "text"
    PHONE = "phone"
    TEXTAREA = "textarea"
    LINK = "link"
    CHECKBOX = "checkbox"
    USER = "user"
    DURATION = "duration"
    IMAGE = "image"
    SELECT = "select"
    NUM = "num"
    FILE = "file"
