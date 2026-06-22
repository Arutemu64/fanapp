from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.vo.notification import NotificationType


class NotificationORM(BaseORM):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column()
    body: Mapped[str] = mapped_column()
    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            native_enum=False,
            create_constraint=True,
            name="notificationtype",
            length=32,
        )
    )
    # In-app deep-link path the notification points to (e.g. "/schedule").
    # Nullable: legacy rows and notifications without a target fall back to root.
    path: Mapped[str | None] = mapped_column()
    mailing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mailings.id", ondelete="CASCADE"),
        index=True,
    )
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Telegram message id of the delivered notification, kept so the message can
    # be deleted when the mailing is recalled. Null until sent to Telegram (or
    # when the user has Telegram notifications disabled). BigInteger: Telegram
    # ids can exceed 32 bits.
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger())

    __table_args__ = (
        # Covers "list user notifications newest first" filter + sort.
        # created_at is inherited from BaseORM, so reference it as SQL text.
        Index(
            "ix_notifications_user_id_created_at",
            "user_id",
            text("created_at DESC"),
        ),
    )
