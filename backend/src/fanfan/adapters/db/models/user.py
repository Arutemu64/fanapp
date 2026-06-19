from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import Enum, Index, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from fanfan.adapters.db.models.base import BaseORM
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
    )
    username: Mapped[str] = mapped_column(index=True, unique=True)
    hashed_password: Mapped[str | None] = mapped_column()
    email: Mapped[str | None] = mapped_column(index=True, unique=True)
    # Notification preferences live in columns (not the settings JSON) so they
    # can be filtered on directly — see read_all_by_receive_all_announcements.
    receive_all_announcements: Mapped[bool] = mapped_column(server_default=text("true"))
    receive_telegram_notifications: Mapped[bool] = mapped_column(
        server_default=text("true")
    )
    # Bag for non-queryable user preferences (e.g. items_per_page).
    settings: Mapped[dict] = mapped_column(JSONB)

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

    ticket: Mapped[TicketORM | None] = relationship(
        foreign_keys="TicketORM.used_by_user_id"
    )
    permissions: Mapped[list[UserPermissionORM]] = relationship(
        cascade="all, delete-orphan"
    )
    social_accounts: Mapped[list[SocialIdentityORM]] = relationship(
        back_populates="user"
    )

    __table_args__ = (
        # Partial index: only TRUE rows are indexed, which is exactly the set
        # the global-announcement fan-out query scans.
        Index(
            "ix_users_receive_all_announcements",
            "receive_all_announcements",
            postgresql_where=text("receive_all_announcements"),
        ),
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.id})"
