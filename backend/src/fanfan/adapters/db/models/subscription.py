from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models import ScheduleItemORM
from fanfan.adapters.db.models.base import BaseORM


class SubscriptionORM(BaseORM):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("schedule_item_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    schedule_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("schedule.id", ondelete="CASCADE")
    )
    counter: Mapped[int] = mapped_column()

    event: Mapped[ScheduleItemORM] = relationship()
