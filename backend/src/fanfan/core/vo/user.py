import enum
import secrets
from typing import NewType
from uuid import UUID, uuid7

UserId = NewType("UserId", UUID)
Username = NewType("Username", str)
UserNumber = NewType("UserNumber", int)


def generate_user_id() -> UserId:
    return UserId(uuid7())


# The seed is not a secret: it is a public input to the avatar generator, only
# unguessable enough that two users do not collide on the same face. URL-safe
# characters keep it printable wherever it is logged or copied.
AVATAR_SEED_PATTERN = r"^[A-Za-z0-9_-]{4,32}$"


def generate_avatar_seed() -> str:
    return secrets.token_urlsafe(9)


# Six digits, never a leading zero, so the number reads the same as an int and
# as typed. Random, not sequential: a counter would publish how many accounts
# exist and let anyone walk them in order.
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

    # TODO: drop the legacy values once a deploy has run for a while — they
    # cover clients still on the old bundle and a TCLOUD__EVENT_IDS_MAP not yet
    # updated.
    # Renaming an enum value is a breaking change (https://google.aip.dev/180),
    # so the old spellings keep resolving; the API schema lists only the new.
    @classmethod
    def _missing_(cls, value: object) -> UserRole | None:
        legacy: dict[str, UserRole] = {"helper": cls.VOLUNTEER, "org": cls.ORGANIZER}
        return legacy.get(str(value))
