from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserRole

if TYPE_CHECKING:
    from fanfan.adapters.db.models.user import UserORM


class TicketORM(BaseORM):
    __tablename__ = "tickets"

    id: Mapped[TicketId] = mapped_column(primary_key=True)
    barcode: Mapped[str] = mapped_column(unique=True)
    role: Mapped[UserRole] = mapped_column(postgresql.ENUM(UserRole))
    issued_by_user_id: Mapped[UserId | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    used_by_user_id: Mapped[UserId | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )

    ticketscloud_ticket_id: Mapped[str | None] = mapped_column(unique=True)

    issued_by: Mapped[UserORM | None] = relationship(foreign_keys=issued_by_user_id)
    used_by_user: Mapped[UserORM | None] = relationship(
        foreign_keys=used_by_user_id,
        back_populates="ticket",
    )

    def __str__(self) -> TicketId:
        return self.id

    @classmethod
    def from_model(cls, model: Ticket):
        return TicketORM(
            id=model.id,
            barcode=model.barcode,
            role=model.role,
            used_by_user_id=model.used_by_user_id,
            issued_by_user_id=model.issued_by_user_id,
            ticketscloud_ticket_id=model.ticketscloud_ticket_id,
        )

    def to_model(self) -> Ticket:
        return Ticket(
            id=self.id,
            barcode=self.barcode,
            role=self.role,
            used_by_user_id=self.used_by_user_id,
            issued_by_user_id=self.issued_by_user_id,
            ticketscloud_ticket_id=self.ticketscloud_ticket_id,
        )
