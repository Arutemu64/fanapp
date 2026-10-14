from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.user import UserRole


class TicketORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "tickets"
    # One row per sale: TicketsCloud resells a refunded ticket id under a new
    # order, so the ticket id alone is not unique.
    __table_args__ = (
        UniqueConstraint(
            "ticketscloud_order_id",
            "ticketscloud_ticket_id",
            name="uq_tickets_ticketscloud_sale",
        ),
    )

    barcode: Mapped[str] = mapped_column(unique=True)
    role: Mapped[UserRole] = str_enum_column(
        UserRole,
        name="userrole",
        default=UserRole.VISITOR,
        server_default=UserRole.VISITOR.value,
    )
    issued_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # SET NULL, not CASCADE: a ticket is an imported/issued artifact that must
    # survive account deletion — the barcode is simply freed for re-linking.
    used_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
    )

    ticketscloud_ticket_id: Mapped[str | None] = mapped_column(index=True)
    ticketscloud_order_id: Mapped[str | None]
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    used_by_user: Mapped[UserORM | None] = relationship(
        foreign_keys=used_by_user_id,
        back_populates="ticket",
        lazy="raise",
    )

    def __str__(self) -> str:
        return str(self.id)
