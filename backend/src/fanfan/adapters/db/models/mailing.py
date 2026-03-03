from uuid import uuid7

from sqlalchemy import UUID, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.vo.user import UserId


class MailingORM(BaseORM):
    __tablename__ = "mailings"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid7
    )
    total: Mapped[int] = mapped_column(default=0)
    is_cancelled: Mapped[bool] = mapped_column(default="False")
    by_user_id: Mapped[UserId | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
