from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM


class PushSubscriptionORM(BaseORM):
    __tablename__ = "push_subs"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    endpoint: Mapped[str] = mapped_column(unique=True)
    p256dh: Mapped[str] = mapped_column()
    auth: Mapped[str] = mapped_column()
