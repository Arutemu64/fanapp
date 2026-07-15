from uuid import UUID

from sqlalchemy import ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.core.vo.mailing import MailingStatus


class MailingORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "mailings"

    status: Mapped[MailingStatus] = str_enum_column(
        MailingStatus,
        name="mailingstatus",
    )
    by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    sent_count: Mapped[int] = mapped_column(server_default=text("0"))
    total_count: Mapped[int] = mapped_column(server_default=text("0"))
