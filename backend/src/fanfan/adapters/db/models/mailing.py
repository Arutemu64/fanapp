from uuid import uuid7

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserId


class MailingORM(BaseORM):
    __tablename__ = "mailings"

    id: Mapped[MailingId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    status: Mapped[MailingStatus] = mapped_column(postgresql.ENUM(MailingStatus))
    by_user_id: Mapped[UserId | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    sent_count: Mapped[int] = mapped_column(default=0)
    total_count: Mapped[int] = mapped_column(default=0)
