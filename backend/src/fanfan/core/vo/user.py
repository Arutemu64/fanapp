import enum
import secrets
from typing import NewType
from uuid import UUID, uuid7

UserId = NewType("UserId", UUID)
Username = NewType("Username", str)


def generate_user_id() -> UserId:
    return UserId(uuid7())


# The seed is not a secret: it is a public input to the avatar generator, only
# unguessable enough that two users do not collide on the same face. URL-safe
# characters keep it printable wherever it is logged or copied.
AVATAR_SEED_PATTERN = r"^[A-Za-z0-9_-]{4,32}$"


def generate_avatar_seed() -> str:
    return secrets.token_urlsafe(9)


class UserRole(enum.StrEnum):
    VISITOR = "visitor"
    PARTICIPANT = "participant"
    HELPER = "helper"
    ORG = "org"
