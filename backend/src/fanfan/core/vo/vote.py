from __future__ import annotations

import enum
from typing import NewType

VoteId = NewType("VoteId", int)


class VotingStatus(enum.StrEnum):
    OPEN = "open"
    NOT_AUTHENTICATED = "not_authenticated"
    NO_TICKET = "no_ticket"
    DISABLED = "disabled"
