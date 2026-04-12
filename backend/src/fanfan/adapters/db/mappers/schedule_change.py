from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.application.dto.schedule_change import (
    ScheduleChangeEventDTO,
    ScheduleChangeFullDTO,
    ScheduleChangeUserDTO,
)
from fanfan.core.models.schedule_change import ScheduleChange


class ScheduleChangeMapper:
    @staticmethod
    def from_model(model: ScheduleChange) -> ScheduleChangeORM:
        return ScheduleChangeORM(
            id=model.id,
            type=model.type,
            mailing_id=model.mailing_id,
            user_id=model.user_id,
            changed_event_id=model.changed_event_id,
            argument_event_id=model.argument_event_id,
            send_global_announcement=model.send_global_announcement,
        )

    @staticmethod
    def to_model(orm: ScheduleChangeORM) -> ScheduleChange:
        return ScheduleChange(
            id=orm.id,
            type=orm.type,
            mailing_id=orm.mailing_id,
            user_id=orm.user_id,
            changed_event_id=orm.changed_event_id,
            argument_event_id=orm.argument_event_id,
            send_global_announcement=orm.send_global_announcement,
        )

    @staticmethod
    def parse_full_dto(
        schedule_change_orm: ScheduleChangeORM,
    ) -> ScheduleChangeFullDTO:
        return ScheduleChangeFullDTO(
            id=schedule_change_orm.id,
            type=schedule_change_orm.type,
            mailing_id=schedule_change_orm.mailing_id,
            user_id=schedule_change_orm.user_id,
            send_global_announcement=schedule_change_orm.send_global_announcement,
            changed_event=ScheduleChangeEventDTO(
                id=schedule_change_orm.changed_event.id,
                public_number=schedule_change_orm.changed_event.public_id,
                title=schedule_change_orm.changed_event.title,
                order=schedule_change_orm.changed_event.order,
            )
            if schedule_change_orm.changed_event
            else None,
            argument_event=ScheduleChangeEventDTO(
                id=schedule_change_orm.argument_event.id,
                public_number=schedule_change_orm.argument_event.public_id,
                title=schedule_change_orm.argument_event.title,
                order=schedule_change_orm.argument_event.order,
            )
            if schedule_change_orm.argument_event
            else None,
            user=ScheduleChangeUserDTO(
                id=schedule_change_orm.user.id,
                username=schedule_change_orm.user.username,
            )
            if schedule_change_orm.user
            else None,
        )
