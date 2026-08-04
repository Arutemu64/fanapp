from dataclasses import dataclass
from typing import Self

from fanfan.core.events.schedule import (
    ScheduleChangeCreated,
    ScheduleChangeUndone,
)
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import (
    ScheduleChangeId,
    ScheduleChangeType,
    generate_schedule_change_id,
)
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class ScheduleChange(AggregateRoot):
    id: ScheduleChangeId
    type: ScheduleChangeType

    changed_event_id: ScheduleEventId | None
    argument_event_id: ScheduleEventId | None

    mailing_id: MailingId | None
    user_id: UserId | None
    next_event_changed: bool

    @classmethod
    def set_as_current(
        cls,
        *,
        changed_event_id: ScheduleEventId | None,
        previous_event_id: ScheduleEventId | None,
        mailing_id: MailingId | None,
        user_id: UserId | None,
    ) -> Self:
        instance = cls(
            id=generate_schedule_change_id(),
            type=ScheduleChangeType.SET_AS_CURRENT,
            changed_event_id=changed_event_id,
            argument_event_id=previous_event_id,
            mailing_id=mailing_id,
            user_id=user_id,
            next_event_changed=True,
        )
        instance.record_event(ScheduleChangeCreated(schedule_change_id=instance.id))
        return instance

    @classmethod
    def moved(
        cls,
        *,
        event_id: ScheduleEventId,
        previous_event_id: ScheduleEventId | None,
        mailing_id: MailingId | None,
        user_id: UserId | None,
        next_event_changed: bool,
    ) -> Self:
        instance = cls(
            id=generate_schedule_change_id(),
            type=ScheduleChangeType.MOVED,
            changed_event_id=event_id,
            argument_event_id=previous_event_id,
            mailing_id=mailing_id,
            user_id=user_id,
            next_event_changed=next_event_changed,
        )
        instance.record_event(ScheduleChangeCreated(schedule_change_id=instance.id))
        return instance

    @classmethod
    def skipped(
        cls,
        *,
        event_id: ScheduleEventId,
        mailing_id: MailingId | None,
        user_id: UserId | None,
        next_event_changed: bool,
    ) -> Self:
        return cls._skip_changed(
            change_type=ScheduleChangeType.SKIPPED,
            event_id=event_id,
            mailing_id=mailing_id,
            user_id=user_id,
            next_event_changed=next_event_changed,
        )

    @classmethod
    def unskipped(
        cls,
        *,
        event_id: ScheduleEventId,
        mailing_id: MailingId | None,
        user_id: UserId | None,
        next_event_changed: bool,
    ) -> Self:
        return cls._skip_changed(
            change_type=ScheduleChangeType.UNSKIPPED,
            event_id=event_id,
            mailing_id=mailing_id,
            user_id=user_id,
            next_event_changed=next_event_changed,
        )

    @classmethod
    def _skip_changed(
        cls,
        *,
        change_type: ScheduleChangeType,
        event_id: ScheduleEventId,
        mailing_id: MailingId | None,
        user_id: UserId | None,
        next_event_changed: bool,
    ) -> Self:
        instance = cls(
            id=generate_schedule_change_id(),
            type=change_type,
            changed_event_id=event_id,
            argument_event_id=None,
            mailing_id=mailing_id,
            user_id=user_id,
            next_event_changed=next_event_changed,
        )
        instance.record_event(ScheduleChangeCreated(schedule_change_id=instance.id))
        return instance

    def mark_undone(self) -> None:
        self.record_event(ScheduleChangeUndone(mailing_id=self.mailing_id))
