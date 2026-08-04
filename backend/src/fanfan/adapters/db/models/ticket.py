from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.user import UserRole


class TicketORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "tickets"

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

    ticketscloud_ticket_id: Mapped[str | None] = mapped_column(unique=True)

    issued_by: Mapped[UserORM | None] = relationship(foreign_keys=issued_by_user_id)
    used_by_user: Mapped[UserORM | None] = relationship(
        foreign_keys=used_by_user_id,
        back_populates="ticket",
    )

    def __str__(self):
        return str(self.id)
