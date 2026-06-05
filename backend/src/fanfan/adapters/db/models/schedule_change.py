from uuid import uuid7

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.adapters.db.models.schedule_event import ScheduleEventORM
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.user import UserId


class ScheduleChangeORM(BaseORM):
    __tablename__ = "schedule_changes"

    id: Mapped[ScheduleChangeId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    # TODO should I use lookup table too?
    type: Mapped[ScheduleChangeType] = mapped_column(
        postgresql.ENUM(ScheduleChangeType)
    )
    changed_event_id: Mapped[ScheduleEventId | None] = mapped_column(
        ForeignKey("schedule.id", ondelete="CASCADE")
    )
    argument_event_id: Mapped[ScheduleEventId | None] = mapped_column(
        ForeignKey("schedule.id", ondelete="CASCADE")
    )
    user_id: Mapped[UserId | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    next_event_changed: Mapped[bool] = mapped_column()
    mailing_id: Mapped[MailingId | None] = mapped_column(
        ForeignKey("mailings.id", ondelete="SET NULL")
    )

    changed_event: Mapped[ScheduleEventORM | None] = relationship(
        foreign_keys=[changed_event_id]
    )
    argument_event: Mapped[ScheduleEventORM | None] = relationship(
        foreign_keys=[argument_event_id]
    )
    user: Mapped[UserORM | None] = relationship(foreign_keys=user_id)
