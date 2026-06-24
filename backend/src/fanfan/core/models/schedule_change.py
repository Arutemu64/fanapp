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
from fanfan.core.vo.schedule_item import ScheduleItemId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class ScheduleChange(AggregateRoot):
    id: ScheduleChangeId
    type: ScheduleChangeType

    # Arguments
    changed_schedule_item_id: ScheduleItemId | None
    argument_schedule_item_id: ScheduleItemId | None

    # Mailing
    mailing_id: MailingId | None
    user_id: UserId | None
    next_event_changed: bool

    @classmethod
    def set_as_current(
        cls,
        *,
        changed_schedule_item_id: ScheduleItemId | None,
        previous_schedule_item_id: ScheduleItemId | None,
        mailing_id: MailingId | None,
        user_id: UserId | None,
    ) -> Self:
        instance = cls(
            id=generate_schedule_change_id(),
            type=ScheduleChangeType.SET_AS_CURRENT,
            changed_schedule_item_id=changed_schedule_item_id,
            argument_schedule_item_id=previous_schedule_item_id,
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
        schedule_item_id: ScheduleItemId,
        previous_schedule_item_id: ScheduleItemId | None,
        mailing_id: MailingId | None,
        user_id: UserId | None,
        next_event_changed: bool,
    ) -> Self:
        instance = cls(
            id=generate_schedule_change_id(),
            type=ScheduleChangeType.MOVED,
            changed_schedule_item_id=schedule_item_id,
            argument_schedule_item_id=previous_schedule_item_id,
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
        schedule_item_id: ScheduleItemId,
        mailing_id: MailingId | None,
        user_id: UserId | None,
        next_event_changed: bool,
    ) -> Self:
        return cls._skip_changed(
            change_type=ScheduleChangeType.SKIPPED,
            schedule_item_id=schedule_item_id,
            mailing_id=mailing_id,
            user_id=user_id,
            next_event_changed=next_event_changed,
        )

    @classmethod
    def unskipped(
        cls,
        *,
        schedule_item_id: ScheduleItemId,
        mailing_id: MailingId | None,
        user_id: UserId | None,
        next_event_changed: bool,
    ) -> Self:
        return cls._skip_changed(
            change_type=ScheduleChangeType.UNSKIPPED,
            schedule_item_id=schedule_item_id,
            mailing_id=mailing_id,
            user_id=user_id,
            next_event_changed=next_event_changed,
        )

    @classmethod
    def _skip_changed(
        cls,
        *,
        change_type: ScheduleChangeType,
        schedule_item_id: ScheduleItemId,
        mailing_id: MailingId | None,
        user_id: UserId | None,
        next_event_changed: bool,
    ) -> Self:
        instance = cls(
            id=generate_schedule_change_id(),
            type=change_type,
            changed_schedule_item_id=schedule_item_id,
            argument_schedule_item_id=None,
            mailing_id=mailing_id,
            user_id=user_id,
            next_event_changed=next_event_changed,
        )
        instance.record_event(ScheduleChangeCreated(schedule_change_id=instance.id))
        return instance

    def mark_undone(self) -> None:
        self.record_event(ScheduleChangeUndone(mailing_id=self.mailing_id))
