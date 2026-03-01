from uuid import uuid7

from sqlalchemy import UUID, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.models.mailing import Mailing
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

    @classmethod
    def from_model(cls, model: Mailing):
        return MailingORM(
            id=model.id,
            total=model.total,
            is_cancelled=model.is_cancelled,
            by_user_id=model.by_user_id,
        )

    def to_model(self) -> Mailing:
        return Mailing(
            id=self.id,
            total=self.total,
            is_cancelled=self.is_cancelled,
            by_user_id=self.by_user_id,
        )
