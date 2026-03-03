from datetime import datetime
from uuid import uuid7

from sqlalchemy import UUID, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models import BaseORM
from fanfan.core.vo.user import UserId


class NotificationTypeORM(BaseORM):
    __tablename__ = "notification_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


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
