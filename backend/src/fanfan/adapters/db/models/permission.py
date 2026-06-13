from uuid import UUID, uuid7

from sqlalchemy import Enum, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.vo.permission import Permissions


class UserPermissionORM(BaseORM):
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

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    permission: Mapped[str] = mapped_column(
        Enum(
            Permissions,
            native_enum=False,
            create_constraint=True,
            name="permissionname",
            length=64,
            # Domain stores the permission *value* ("schedule:manage"), not the
            # enum member name, so emit values for both storage and the CHECK.
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        index=True,
    )
    object_id: Mapped[int | None] = mapped_column()
    object_type: Mapped[str | None] = mapped_column()
