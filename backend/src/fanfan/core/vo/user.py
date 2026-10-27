import enum
import secrets
from typing import NewType
from uuid import UUID, uuid7

UserId = NewType("UserId", UUID)
Username = NewType("Username", str)
UserNumber = NewType("UserNumber", int)


# Seeded by the initial migration; cron, the CLI and NATS consumers act as it.
SYSTEM_USER_ID = UserId(UUID("00000000-0000-0000-0000-000000000000"))
# Seeded by migration 4b8e2d6f1a37; the stage console's webhook acts as it.
STAGE_CONSOLE_USER_ID = UserId(UUID("00000000-0000-0000-0000-000000000001"))


def generate_user_id() -> UserId:
    return UserId(uuid7())


AVATAR_SEED_PATTERN = r"^[A-Za-z0-9_-]{4,32}$"


def generate_avatar_seed() -> str:
    return secrets.token_urlsafe(9)


USER_NUMBER_MIN = 100_000
USER_NUMBER_MAX = 999_999


def generate_user_number() -> UserNumber:
    span = USER_NUMBER_MAX - USER_NUMBER_MIN + 1
    return UserNumber(USER_NUMBER_MIN + secrets.randbelow(span))


class UserRole(enum.StrEnum):
    VISITOR = "visitor"
    PARTICIPANT = "participant"
    VOLUNTEER = "volunteer"
    ORGANIZER = "organizer"
