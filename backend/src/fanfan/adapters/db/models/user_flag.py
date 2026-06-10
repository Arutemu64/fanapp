from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM


class UserFlagORM(BaseORM):
    __tablename__ = "user_flags"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    name: Mapped[str] = mapped_column()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
