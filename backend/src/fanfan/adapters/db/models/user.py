from typing import TYPE_CHECKING

from sqlalchemy import Index, func, text
from sqlalchemy.dialects.postgresql import JSONB
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

    # Uniqueness is enforced case-insensitively via ix_users_username_lower
    # (see __table_args__) so lookups by lower(username) hit an index and
    # "Alice" / "alice" can never coexist.
    username: Mapped[str] = mapped_column()
    hashed_password: Mapped[str | None] = mapped_column()
    email: Mapped[str | None] = mapped_column(index=True, unique=True)
    # Notification preferences live in columns (not the settings JSON) so they
    # can be filtered on directly — see read_all_by_receive_all_announcements.
    # Deliberately NOT indexed: the column defaults to true, so the fan-out
    # query matches ~every row and the planner seq-scans regardless. A partial
    # index on the same column it filters by also stores no information — the
    # predicate already pins the value — so it was pure write overhead.
    receive_all_announcements: Mapped[bool] = mapped_column(server_default=text("true"))
    receive_telegram_notifications: Mapped[bool] = mapped_column(
        server_default=text("true")
    )
    receive_vk_notifications: Mapped[bool] = mapped_column(server_default=text("true"))
    # Bag for non-queryable user preferences. Currently empty; kept as an
    # extension point so new prefs need no schema migration.
    settings: Mapped[dict] = mapped_column(JSONB)

    # Indexed for the broadcast fan-out (read_all_by_roles): the org/helper roles
    # are a tiny slice of a table dominated by visitors, so targeting them was a
    # full scan. The planner still ignores the index when a broadcast includes
    # VISITOR, which is correct — that really is most of the table.
    role: Mapped[UserRole] = str_enum_column(
        UserRole,
        name="userrole",
        default=UserRole.VISITOR,
        server_default=UserRole.VISITOR.value,
        index=True,
    )

    ticket: Mapped[TicketORM | None] = relationship(
        foreign_keys="TicketORM.used_by_user_id"
    )
    permissions: Mapped[list[UserPermissionORM]] = relationship(
        cascade="all, delete-orphan"
    )
    social_identities: Mapped[list[SocialIdentityORM]] = relationship()

    __table_args__ = (
        # Case-insensitive uniqueness; get_by_username compares lower(username),
        # so this expression index is also what makes login lookups indexed.
        Index("ix_users_username_lower", func.lower(username), unique=True),
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.id})"
