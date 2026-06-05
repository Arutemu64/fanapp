from typing import NewType
from uuid import UUID, uuid7

NominationId = NewType("NominationId", UUID)
NominationCode = NewType("NominationCode", str)


def generate_nomination_id() -> NominationId:
    return NominationId(uuid7())
