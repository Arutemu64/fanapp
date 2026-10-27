from dataclasses import dataclass
from typing import Self

from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import TicketBatchId
from fanfan.core.vo.user import UserId, UserRole


@dataclass(slots=True, kw_only=True)
class TicketBatch:
    """Tickets an organizer generated in one request.

    The client picks the id, so a repeated request finds the batch and gets its
    barcodes back instead of a second batch (ADR-0034).
    """

    id: TicketBatchId
    role: UserRole
    amount: int
    issued_by_user_id: UserId | None
    tickets: list[Ticket]

    @classmethod
    def issue(
        cls,
        *,
        batch_id: TicketBatchId,
        role: UserRole,
        amount: int,
        issued_by_user_id: UserId,
    ) -> Self:
        batch = cls(
            id=batch_id,
            role=role,
            amount=amount,
            issued_by_user_id=issued_by_user_id,
            tickets=[
                Ticket.issue(
                    role=role, issued_by_user_id=issued_by_user_id, batch_id=batch_id
                )
                for _ in range(amount)
            ],
        )
        batch._ensure_unique_barcodes()
        return batch

    @property
    def barcodes(self) -> list[str]:
        return [ticket.barcode for ticket in self.tickets]

    def redraw_barcodes(self) -> None:
        """Draw every barcode again, after one turned out to be taken."""
        for ticket in self.tickets:
            ticket.redraw_barcode()
        self._ensure_unique_barcodes()

    def is_same_request(
        self, *, by_user_id: UserId, role: UserRole, amount: int
    ) -> bool:
        return (
            self.issued_by_user_id == by_user_id
            and self.role == role
            and self.amount == amount
        )

    def _ensure_unique_barcodes(self) -> None:
        seen: set[str] = set()
        for ticket in self.tickets:
            while ticket.barcode in seen:
                ticket.redraw_barcode()
            seen.add(ticket.barcode)
