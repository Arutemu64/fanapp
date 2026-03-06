from uuid import uuid7

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserRole


class TicketORM(BaseORM):
    __tablename__ = "tickets"

    id: Mapped[TicketId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    barcode: Mapped[str] = mapped_column(unique=True)
    role: Mapped[UserRole] = mapped_column(
        postgresql.ENUM(UserRole),
        default=UserRole.VISITOR,
        server_default="VISITOR",
    )
    issued_by_user_id: Mapped[UserId | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    used_by_user_id: Mapped[UserId | None] = mapped_column(
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

    def __str__(self) -> TicketId:
        return TicketId(self.id)
