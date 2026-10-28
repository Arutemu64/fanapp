from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.mailing import MailingStatus


class MailingORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "mailings"
    __table_args__ = (
        CheckConstraint("total_count >= 0", name="total_count_not_negative"),
    )

    status: Mapped[MailingStatus] = str_enum_column(
        MailingStatus,
        name="mailingstatus",
    )
    by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    by_user: Mapped[UserORM | None] = relationship(
        foreign_keys=by_user_id, lazy="raise"
    )

    body: Mapped[str | None] = mapped_column()
    roles: Mapped[list[str] | None] = mapped_column(JSONB)

    total_count: Mapped[int] = mapped_column(server_default=text("0"))
