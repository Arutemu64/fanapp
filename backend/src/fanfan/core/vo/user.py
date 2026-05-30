from __future__ import annotations

import enum
from typing import NewType
from uuid import UUID, uuid7

UserId = NewType("UserId", UUID)
Username = NewType("Username", str)


def generate_user_id() -> UserId:
    return UserId(uuid7())


class UserRole(enum.StrEnum):
    VISITOR = ("visitor", "Зритель", "Зрители")
    PARTICIPANT = ("participant", "Участник", "Участники")
    HELPER = ("helper", "Волонтёр", "Волонтёры")
    ORG = ("org", "Организатор", "Организаторы")

    def __new__(cls, value, label, label_plural):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.label_plural = label_plural
        return obj

    def __str__(self):
        return self.label
