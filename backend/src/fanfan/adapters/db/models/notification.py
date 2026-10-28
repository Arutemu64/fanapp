from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.core.vo.notification import NotificationType


class NotificationORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column()
    body: Mapped[str] = mapped_column()
    type: Mapped[NotificationType] = str_enum_column(
        NotificationType,
        name="notificationtype",
    )
    path: Mapped[str | None] = mapped_column()
    mailing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mailings.id", ondelete="SET NULL"),
        index=True,
    )
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # No FK on purpose: it only keys the push collapse topic (adapters/push/push.py).
    # A dangling id still keys it; SET NULL would merge other events' pushes.
    event_id: Mapped[UUID | None] = mapped_column()

    __table_args__ = (
        Index(
            "ix_notifications_user_id_created_at",
            "user_id",
            text("created_at DESC"),
        ),
        Index("ix_notifications_created_at", "created_at"),
    )
