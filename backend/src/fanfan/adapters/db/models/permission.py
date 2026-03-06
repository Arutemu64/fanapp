from uuid import uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.permission import (
    PermissionId,
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
    UserPermissionId,
)
from fanfan.core.vo.user import UserId


class UserPermissionORM(BaseORM):
    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_id", "object_id", "object_type"),
    )

    id: Mapped[UserPermissionId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UserId] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    permission_id: Mapped[PermissionId] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE")
    )
    object_id: Mapped[PermissionObjectId | None] = mapped_column()
    object_type: Mapped[PermissionObjectType | None] = mapped_column()

    permission: Mapped["PermissionORM"] = relationship(lazy="joined")


class PermissionORM(BaseORM):
    __tablename__ = "permissions"

    id: Mapped[PermissionId] = mapped_column(primary_key=True)
    name: Mapped[PermissionName] = mapped_column(unique=True)
