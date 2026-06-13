from uuid import UUID, uuid7

from sqlalchemy import Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.user import UserRole


class TicketORM(BaseORM):
    __tablename__ = "tickets"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    barcode: Mapped[str] = mapped_column(unique=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=False,
            create_constraint=True,
            name="userrole",
            length=32,
        ),
        default=UserRole.VISITOR,
        server_default="VISITOR",
    )
    issued_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    used_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )

    # Ticketscloud
    ticketscloud_ticket_id: Mapped[str | None] = mapped_column(unique=True)

    issued_by: Mapped[UserORM | None] = relationship(foreign_keys=issued_by_user_id)
    used_by_user: Mapped[UserORM | None] = relationship(
        foreign_keys=used_by_user_id,
        back_populates="ticket",
    )

    def __str__(self):
        return str(self.id)
