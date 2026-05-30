from typing import NewType
from uuid import UUID, uuid7

UserFlagId = NewType("UserFlagId", UUID)


def generate_user_flag_id() -> UserFlagId:
    return UserFlagId(uuid7())
