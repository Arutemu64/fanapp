from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.core.vo.permission import Permission


class UserPermissionORM(UUIDPrimaryKeyMixin, BaseORM):
    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", "permission"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    permission: Mapped[str] = str_enum_column(
        Permission,
        name="permissionname",
        length=64,
        index=True,
    )
