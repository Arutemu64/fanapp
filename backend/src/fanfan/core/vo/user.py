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
    # The values are older than the member names and stay put: stored rows, the
    # API contract and TCLOUD__EVENT_IDS_MAP all carry them, and renaming an enum
    # value is a breaking change (https://google.aip.dev/180).
    VISITOR = "visitor"
    PARTICIPANT = "participant"
    VOLUNTEER = "helper"
    ORGANIZER = "org"
