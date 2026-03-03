from __future__ import annotations

import enum
from typing import NewType
from uuid import UUID

ParticipantId = NewType("ParticipantId", UUID)
ParticipantVotingNumber = NewType("ParticipantVotingNumber", int)


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
