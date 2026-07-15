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
    # In-app deep-link path the notification points to (e.g. "/schedule").
    # Nullable: legacy rows and notifications without a target fall back to root.
    path: Mapped[str | None] = mapped_column()
    # SET NULL, not CASCADE: cancelling a mailing already deletes its
    # undelivered notifications explicitly (DeleteMailingNotifications), so a
    # hard delete of an old mailing row must not wipe delivered notifications
    # out of users' inboxes.
    mailing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mailings.id", ondelete="SET NULL"),
        index=True,
    )
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # Covers "list user notifications newest first" filter + sort.
        # created_at is inherited from BaseORM, so reference it as SQL text.
        Index(
            "ix_notifications_user_id_created_at",
            "user_id",
            text("created_at DESC"),
        ),
    )
