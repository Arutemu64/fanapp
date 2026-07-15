from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.schedule_event import ScheduleEventORM
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.schedule_change import ScheduleChangeType


class ScheduleChangeORM(UUIDPrimaryKeyMixin, BaseORM):
    __tablename__ = "schedule_changes"

    type: Mapped[ScheduleChangeType] = str_enum_column(
        ScheduleChangeType,
        name="schedulechangetype",
    )
    changed_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schedule_events.id", ondelete="CASCADE"), index=True
    )
    argument_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schedule_events.id", ondelete="CASCADE"), index=True
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
