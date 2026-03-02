from __future__ import annotations

import enum
from typing import NewType
from uuid import UUID

VoteId = NewType("VoteId", UUID)


class VotingStatus(enum.StrEnum):
    OPEN = "open"
    NOT_AUTHENTICATED = "not_authenticated"
    NO_TICKET = "no_ticket"
    DISABLED = "disabled"
