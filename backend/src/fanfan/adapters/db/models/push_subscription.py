from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin


class PushSubscriptionORM(UUIDPrimaryKeyMixin, BaseORM):
    __tablename__ = "push_subs"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    endpoint: Mapped[str] = mapped_column(unique=True)
    p256dh: Mapped[str] = mapped_column()
    auth: Mapped[str] = mapped_column()
