from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.core.vo.user_flag import UserFlagName


class UserFlagORM(UUIDPrimaryKeyMixin, BaseORM):
    __tablename__ = "user_flags"
    # A flag is set-like: a user either has it or not, never twice.
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    name: Mapped[UserFlagName] = str_enum_column(
        UserFlagName,
        name="userflagname",
        length=64,
    )
    # No standalone index: user_id is the leading column of the unique
    # constraint above, which already covers user_id lookups.
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
