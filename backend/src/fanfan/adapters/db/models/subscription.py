from uuid import uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models import ScheduleEventORM
from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionORM(BaseORM):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    id: Mapped[SubscriptionId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UserId] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_id: Mapped[ScheduleEventId] = mapped_column(
        ForeignKey("schedule.id", ondelete="CASCADE")
    )
    counter: Mapped[int] = mapped_column()

    event: Mapped[ScheduleEventORM] = relationship()
