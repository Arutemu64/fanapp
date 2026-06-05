from datetime import datetime
from uuid import uuid7

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.user import UserId


class NotificationORM(BaseORM):
    __tablename__ = "notifications"

    id: Mapped[NotificationId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UserId] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column()
    body: Mapped[str] = mapped_column()
    type: Mapped[NotificationType] = mapped_column(postgresql.ENUM(NotificationType))
    mailing_id: Mapped[MailingId | None] = mapped_column(
        ForeignKey("mailings.id", ondelete="CASCADE")
    )
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
