import enum
from typing import NewType
from uuid import UUID, uuid7

UserFlagId = NewType("UserFlagId", UUID)


def generate_user_flag_id() -> UserFlagId:
    return UserFlagId(uuid7())


class UserFlagName(enum.StrEnum):
    # Set once a user has voted in every votable nomination; cleared otherwise.
    VOTING_CONTEST = "voting_contest"
