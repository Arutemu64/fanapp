from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM


class UserFlagORM(BaseORM):
    __tablename__ = "user_flags"
    # A flag is set-like: a user either has it or not, never twice.
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    name: Mapped[str] = mapped_column()
    # No standalone index: user_id is the leading column of the unique
    # constraint above, which already covers user_id lookups.
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
