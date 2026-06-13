from uuid import UUID, uuid7

from sqlalchemy import Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.vo.mailing import MailingStatus


class MailingORM(BaseORM):
    __tablename__ = "mailings"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    status: Mapped[MailingStatus] = mapped_column(
        Enum(
            MailingStatus,
            native_enum=False,
            create_constraint=True,
            name="mailingstatus",
            length=32,
        )
    )
    by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    sent_count: Mapped[int] = mapped_column(default=0)
    total_count: Mapped[int] = mapped_column(default=0)
