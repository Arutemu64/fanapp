from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models import ScheduleEventORM
from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin


class SubscriptionORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("schedule_events.id", ondelete="CASCADE")
    )
    counter: Mapped[int] = mapped_column()

    event: Mapped[ScheduleEventORM] = relationship()
