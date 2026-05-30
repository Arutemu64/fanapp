from __future__ import annotations

from typing import NewType
from uuid import UUID, uuid7

TicketId = NewType("TicketId", UUID)


def generate_ticket_id() -> TicketId:
    return TicketId(uuid7())
