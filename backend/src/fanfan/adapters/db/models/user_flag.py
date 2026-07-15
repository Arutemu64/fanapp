from uuid import UUID, uuid7

from sqlalchemy import Enum, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.vo.user_flag import UserFlagName


class UserFlagORM(BaseORM):
    __tablename__ = "user_flags"
    # A flag is set-like: a user either has it or not, never twice.
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    name: Mapped[UserFlagName] = mapped_column(
        Enum(
            UserFlagName,
            native_enum=False,
            create_constraint=True,
            name="userflagname",
            length=64,
            # Domain stores the enum *value* ("voting_contest"), not the member
            # name, so emit values for both storage and the CHECK constraint.
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        )
    )
    # No standalone index: user_id is the leading column of the unique
    # constraint above, which already covers user_id lookups.
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
