from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import DateTime, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.user import UserRole

if TYPE_CHECKING:
    from fanfan.adapters.db.models.permission import UserPermissionORM
    from fanfan.adapters.db.models.social_account import SocialIdentityORM
    from fanfan.adapters.db.models.ticket import TicketORM


class UserORM(BaseORM):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    username: Mapped[str | None] = mapped_column(index=True, unique=True)
    hashed_password: Mapped[str | None] = mapped_column()
    email: Mapped[str | None] = mapped_column(index=True, unique=True)
    pending_email: Mapped[str | None] = mapped_column(index=True, unique=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settings: Mapped[dict] = mapped_column(JSONB)

    first_name: Mapped[str | None] = mapped_column()
    role: Mapped[UserRole] = mapped_column(
        postgresql.ENUM(UserRole),
        default=UserRole.VISITOR,
        server_default="VISITOR",
    )

    ticket: Mapped[TicketORM | None] = relationship(
        foreign_keys="TicketORM.used_by_user_id"
    )
    permissions: Mapped[list[UserPermissionORM]] = relationship(
        cascade="all, delete-orphan"
    )
    social_accounts: Mapped[list[SocialIdentityORM]] = relationship(
        back_populates="user"
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.id})"
