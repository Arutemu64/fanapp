from datetime import datetime
from typing import override
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
    __table_args__ = (
        UniqueConstraint("ticketscloud_order_id", "ticketscloud_ticket_id"),
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
    used_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
    )

    ticketscloud_ticket_id: Mapped[str | None] = mapped_column(index=True)
    ticketscloud_order_id: Mapped[str | None]
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ticket_batches.id", ondelete="SET NULL"), index=True
    )

    used_by_user: Mapped[UserORM | None] = relationship(
        foreign_keys=used_by_user_id,
        back_populates="ticket",
        lazy="raise",
    )

    @override
    def __str__(self) -> str:
        return str(self.id)
