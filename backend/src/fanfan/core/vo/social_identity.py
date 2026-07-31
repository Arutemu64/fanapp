from enum import StrEnum
from typing import NewType
from uuid import UUID, uuid7

SocialIdentityId = NewType("SocialIdentityId", UUID)


class SocialProvider(StrEnum):
    """External identity providers the app accepts.

    Doubles as the `iss` stand-in when matching an identity: there is exactly one
    issuer per member, so `(provider, subject)` is the `(iss, sub)` pair OpenID
    Connect asks relying parties to key on. Adding a member means adding an
    Authlib client in `main/ioc/auth.py`, its **own** callback URI (RFC 9700
    §4.4.2.2 — see the module docstring in `presentation/web/oauth.py`), and a
    hand-written migration for the CHECK constraint backing the column.
    """

    TELEGRAM = "telegram"


def generate_social_identity_id() -> SocialIdentityId:
    return SocialIdentityId(uuid7())
