from uuid import UUID, uuid7

from sqlalchemy import Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.schedule_event import ScheduleEventORM
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.schedule_change import ScheduleChangeType


class ScheduleChangeORM(BaseORM):
    __tablename__ = "schedule_changes"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    type: Mapped[ScheduleChangeType] = mapped_column(
        Enum(
            ScheduleChangeType,
            native_enum=False,
            create_constraint=True,
            name="schedulechangetype",
            length=32,
        )
    )
    changed_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schedule.id", ondelete="CASCADE"), index=True
    )
    argument_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schedule.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    next_event_changed: Mapped[bool] = mapped_column()
    mailing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("mailings.id", ondelete="SET NULL"), index=True
    )

    changed_event: Mapped[ScheduleEventORM | None] = relationship(
        foreign_keys=[changed_event_id]
    )
    argument_event: Mapped[ScheduleEventORM | None] = relationship(
        foreign_keys=[argument_event_id]
    )
    user: Mapped[UserORM | None] = relationship(foreign_keys=user_id)
