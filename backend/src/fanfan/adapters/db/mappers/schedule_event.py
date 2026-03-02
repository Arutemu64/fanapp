from fanfan.adapters.db.models import ScheduleEventORM, SubscriptionORM
from fanfan.core.dto.schedule import ScheduleEventFullDTO, ScheduleEventSubscriptionDTO
from fanfan.core.models.schedule_event import ScheduleEvent


class ScheduleEventMapper:
    @staticmethod
    def from_model(model: ScheduleEvent):
        return ScheduleEventORM(
            id=model.id,
            public_id=model.public_number,
            title=model.title,
            duration=model.duration,
            is_current=model.is_current,
            is_skipped=model.is_skipped,
            order=model.order,
            nomination_title=model.nomination_title,
            block_title=model.block_title,
        )

    @staticmethod
    def to_model(orm: ScheduleEventORM) -> ScheduleEvent:
        return ScheduleEvent(
            id=orm.id,
            public_number=orm.public_id,
            title=orm.title,
            duration=orm.duration,
            is_current=orm.is_current,
            is_skipped=orm.is_skipped,
            order=orm.order,
            nomination_title=orm.nomination_title,
            block_title=orm.block_title,
        )

    @staticmethod
    def parse_full_dto(
        event_orm: ScheduleEventORM, subscription_orm: SubscriptionORM | None
    ) -> ScheduleEventFullDTO:
        return ScheduleEventFullDTO(
            id=event_orm.id,
            public_number=event_orm.public_id,
            title=event_orm.title,
            duration=event_orm.duration,
            order=event_orm.order,
            is_current=event_orm.is_current,
            is_skipped=event_orm.is_skipped,
            nomination_title=event_orm.nomination_title,
            block_title=event_orm.block_title,
            queue=event_orm.queue,
            time_until=event_orm.time_until,
            user_subscription=ScheduleEventSubscriptionDTO(
                id=subscription_orm.id,
                counter=subscription_orm.counter,
            )
            if subscription_orm
            else None,
        )
