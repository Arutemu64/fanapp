from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.application.dto.schedule_change import (
    ScheduleChangeFullDTO,
    ScheduleChangeScheduleItemDTO,
    ScheduleChangeUserDTO,
)
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_item import ScheduleItemId
from fanfan.core.vo.user import UserId


class ScheduleChangeMapper:
    @staticmethod
    def from_model(model: ScheduleChange) -> ScheduleChangeORM:
        return ScheduleChangeORM(
            id=model.id,
            type=model.type,
            mailing_id=model.mailing_id,
            user_id=model.user_id,
            changed_schedule_item_id=model.changed_schedule_item_id,
            argument_schedule_item_id=model.argument_schedule_item_id,
            next_event_changed=model.next_event_changed,
        )

    @staticmethod
    def to_model(orm: ScheduleChangeORM) -> ScheduleChange:
        return ScheduleChange(
            id=ScheduleChangeId(orm.id),
            type=orm.type,
            mailing_id=MailingId(orm.mailing_id)
            if orm.mailing_id is not None
            else None,
            user_id=UserId(orm.user_id) if orm.user_id is not None else None,
            changed_schedule_item_id=ScheduleItemId(orm.changed_schedule_item_id)
            if orm.changed_schedule_item_id is not None
            else None,
            argument_schedule_item_id=ScheduleItemId(orm.argument_schedule_item_id)
            if orm.argument_schedule_item_id is not None
            else None,
            next_event_changed=orm.next_event_changed,
        )

    @staticmethod
    def parse_full_dto(
        schedule_change_orm: ScheduleChangeORM,
    ) -> ScheduleChangeFullDTO:
        return ScheduleChangeFullDTO(
            id=ScheduleChangeId(schedule_change_orm.id),
            type=schedule_change_orm.type,
            mailing_id=MailingId(schedule_change_orm.mailing_id)
            if schedule_change_orm.mailing_id is not None
            else None,
            user_id=UserId(schedule_change_orm.user_id)
            if schedule_change_orm.user_id is not None
            else None,
            next_event_changed=schedule_change_orm.next_event_changed,
            changed_schedule_item=ScheduleChangeScheduleItemDTO(
                id=ScheduleItemId(schedule_change_orm.changed_schedule_item.id),
                number=schedule_change_orm.changed_schedule_item.number,
                title=schedule_change_orm.changed_schedule_item.title,
                order=schedule_change_orm.changed_schedule_item.order,
            )
            if schedule_change_orm.changed_schedule_item
            else None,
            argument_schedule_item=ScheduleChangeScheduleItemDTO(
                id=ScheduleItemId(schedule_change_orm.argument_schedule_item.id),
                number=schedule_change_orm.argument_schedule_item.number,
                title=schedule_change_orm.argument_schedule_item.title,
                order=schedule_change_orm.argument_schedule_item.order,
            )
            if schedule_change_orm.argument_schedule_item
            else None,
            user=ScheduleChangeUserDTO(
                id=UserId(schedule_change_orm.user.id),
                username=schedule_change_orm.user.username,
            )
            if schedule_change_orm.user
            else None,
        )
