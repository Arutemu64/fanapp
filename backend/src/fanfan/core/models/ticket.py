from __future__ import annotations

from dataclasses import dataclass

from fanfan.core.exceptions.tickets import TicketAlreadyUsed
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserRole


@dataclass(slots=True, kw_only=True)
class Ticket:
    id: TicketId | None = None
    barcode: str
    role: UserRole
    used_by_user_id: UserId | None
    issued_by_user_id: UserId | None

    ticketscloud_ticket_id: str | None

    def set_as_used(self, user_id: UserId):
        if self.used_by_user_id is not None:
            raise TicketAlreadyUsed
        self.used_by_user_id = user_id
