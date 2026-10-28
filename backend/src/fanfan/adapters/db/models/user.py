from typing import TYPE_CHECKING, override

from sqlalchemy import CheckConstraint, Index, func, text
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.core.vo.user import UserRole

if TYPE_CHECKING:
    from fanfan.adapters.db.models.permission import UserPermissionORM
    from fanfan.adapters.db.models.social_identity import SocialIdentityORM
    from fanfan.adapters.db.models.ticket import TicketORM


class UserORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column()
    hashed_password: Mapped[str | None] = mapped_column()
    email: Mapped[str | None] = mapped_column(index=True, unique=True)
    avatar_seed: Mapped[str] = mapped_column()
    number: Mapped[int] = mapped_column(unique=True)
    receive_all_announcements: Mapped[bool] = mapped_column(
        server_default=text("false")
    )
    receive_telegram_notifications: Mapped[bool] = mapped_column(
        server_default=text("true")
    )
    receive_vk_notifications: Mapped[bool] = mapped_column(server_default=text("true"))

    role: Mapped[UserRole] = str_enum_column(
        UserRole,
        name="userrole",
        default=UserRole.VISITOR,
        server_default=UserRole.VISITOR.value,
        index=True,
    )

    ticket: Mapped[TicketORM | None] = relationship(
        foreign_keys="TicketORM.used_by_user_id",
        lazy="raise",
    )
    permissions: Mapped[list[UserPermissionORM]] = relationship(
        cascade="all, delete-orphan",
        lazy="raise",
    )
    social_identities: Mapped[list[SocialIdentityORM]] = relationship(lazy="raise")

    __table_args__ = (
        Index("ix_users_username_lower", func.lower(username), unique=True),
        # Mirrors normalize_email(), so case variants can't dodge the unique index.
        CheckConstraint("email = lower(btrim(email))", name="email_normalized"),
    )

    @override
    def __str__(self) -> str:
        return f"{self.username} ({self.id})"
