from typing import NewType
from uuid import UUID, uuid7

SocialIdentityId = NewType("SocialIdentityId", UUID)


def generate_social_identity_id() -> SocialIdentityId:
    return SocialIdentityId(uuid7())
