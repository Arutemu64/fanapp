from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM


class UserPermissionORM(BaseORM):
    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_id", "object_id", "object_type"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE")
    )
    object_id: Mapped[int | None] = mapped_column()
    object_type: Mapped[str | None] = mapped_column()

    permission: Mapped[PermissionORM] = relationship(lazy="joined")


class PermissionORM(BaseORM):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
