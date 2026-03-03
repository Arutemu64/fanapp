from uuid import uuid7

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.vo.user import UserId
from fanfan.core.vo.user_flag import UserFlagId


class UserFlagORM(BaseORM):
    __tablename__ = "user_flags"

    id: Mapped[UserFlagId] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid7
    )
    name: Mapped[str] = mapped_column()
    user_id: Mapped[UserId] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
