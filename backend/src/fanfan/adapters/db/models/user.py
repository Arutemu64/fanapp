from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid7

from adaptix import Retort
from sqlalchemy import Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.user import UserId, Username, UserRole

if TYPE_CHECKING:
    from fanfan.adapters.db.models.permission import UserPermissionORM
    from fanfan.adapters.db.models.social_account import SocialAccountORM
    from fanfan.adapters.db.models.ticket import TicketORM


retort = Retort()


class UserORM(BaseORM):
    __tablename__ = "users"

    id: Mapped[UserId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    username: Mapped[Username | None] = mapped_column(index=True, unique=True)
    hashed_password: Mapped[str | None] = mapped_column()
    email: Mapped[str | None] = mapped_column(index=True, unique=True)
    is_verified: Mapped[bool] = mapped_column(server_default="false")
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
    social_accounts: Mapped[list[SocialAccountORM]] = relationship(
        back_populates="user"
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.id})"
