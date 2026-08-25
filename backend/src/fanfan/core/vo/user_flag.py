import enum
from typing import NewType
from uuid import UUID, uuid7

UserFlagId = NewType("UserFlagId", UUID)


def generate_user_flag_id() -> UserFlagId:
    return UserFlagId(uuid7())


class UserFlagName(enum.StrEnum):
    # Per-user boolean markers. None is defined right now — the flag system is kept
    # for future markers. Adding a member also needs a hand-written CHECK-constraint
    # swap migration (Alembic does not diff CHECK bodies); see the fanfan-migrations
    # skill.
    pass
