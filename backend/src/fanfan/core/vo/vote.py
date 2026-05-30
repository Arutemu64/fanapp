from __future__ import annotations

import enum
from typing import NewType
from uuid import UUID, uuid7

VoteId = NewType("VoteId", UUID)


def generate_vote_id() -> VoteId:
    return VoteId(uuid7())


class VotingStatus(enum.StrEnum):
    OPEN = "open"
    NOT_AUTHENTICATED = "not_authenticated"
    NO_TICKET = "no_ticket"
    DISABLED = "disabled"
