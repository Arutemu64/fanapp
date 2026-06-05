from __future__ import annotations

import enum
from typing import NewType
from uuid import UUID, uuid7

UserId = NewType("UserId", UUID)
Username = NewType("Username", str)


def generate_user_id() -> UserId:
    return UserId(uuid7())


class UserRole(enum.StrEnum):
    VISITOR = "visitor"
    PARTICIPANT = "participant"
    HELPER = "helper"
    ORG = "org"
