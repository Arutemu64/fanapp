from datetime import datetime
from uuid import uuid7

from sqlalchemy import UUID, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models import BaseORM
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.user import UserId


class NotificationORM(BaseORM):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id: Mapped[UserId] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column()
    body: Mapped[str] = mapped_column()
    type: Mapped[str] = mapped_column()
    mailing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mailings.id", ondelete="CASCADE")
    )
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @classmethod
    def from_model(cls, model: Notification) -> NotificationORM:
        return NotificationORM(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            body=model.body,
            type=model.type,
            mailing_id=model.mailing_id,
            seen_at=model.seen_at,
        )

    def to_model(self) -> Notification:
        return Notification(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            body=self.body,
            type=NotificationType(self.type),
            mailing_id=self.mailing_id,
            seen_at=self.seen_at,
        )
