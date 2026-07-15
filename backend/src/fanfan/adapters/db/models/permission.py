from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.core.vo.permission import Permissions


class UserPermissionORM(UUIDPrimaryKeyMixin, BaseORM):
    __tablename__ = "user_permissions"
    __table_args__ = (
        # object_id / object_type are nullable; without NULLS NOT DISTINCT
        # Postgres treats NULL != NULL, so a user could be granted the same
        # global (unscoped) permission any number of times. PG15+ required.
        UniqueConstraint(
            "user_id",
            "permission",
            "object_id",
            "object_type",
            postgresql_nulls_not_distinct=True,
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    permission: Mapped[str] = str_enum_column(
        Permissions,
        name="permissionname",
        length=64,
        index=True,
    )
    object_id: Mapped[int | None] = mapped_column()
    object_type: Mapped[str | None] = mapped_column()
