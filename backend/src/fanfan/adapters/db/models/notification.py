from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.notification import NotificationType


class NotificationORM(BaseORM):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column()
    body: Mapped[str] = mapped_column()
    type: Mapped[NotificationType] = mapped_column(postgresql.ENUM(NotificationType))
    mailing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mailings.id", ondelete="CASCADE"),
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
