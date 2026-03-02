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

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.user import UserId, Username, UserRole

if TYPE_CHECKING:
    from fanfan.adapters.db.models.permission import UserPermissionORM
    from fanfan.adapters.db.models.social_account import SocialAccountORM
    from fanfan.adapters.db.models.ticket import TicketORM


retort = Retort()


class UserORM(BaseORM):
    __tablename__ = "users"

    id: Mapped[UserId] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid7
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
        back_populates="user", cascade="all, delete-orphan"
    )
    social_accounts: Mapped[list[SocialAccountORM]] = relationship(
        back_populates="user"
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.id})"

    @classmethod
    def from_model(cls, model: User):
        return UserORM(
            id=model.id,
            username=model.username,
            hashed_password=model.hashed_password,
            email=model.email,
            first_name=model.first_name,
            role=model.role,
            settings=retort.dump(model.settings),
            is_verified=model.is_verified,
        )

    def to_model(self) -> User:
        return User(
            id=UserId(self.id),
            username=self.username,
            hashed_password=self.hashed_password,
            email=self.email,
            first_name=self.first_name,
            role=UserRole(self.role),
            settings=retort.load(self.settings, UserSettings),
            is_verified=self.is_verified,
        )
