from fanfan.adapters.db.models import ScheduleEventORM
from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.schedule_event import ScheduleEventId


class ScheduleEventMapper:
    @staticmethod
    def from_model(model: ScheduleEvent):
        return ScheduleEventORM(
            id=model.id,
            number=model.number,
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
            id=ScheduleEventId(orm.id),
            number=orm.number,
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
        event_orm: ScheduleEventORM,
        *,
        queue: int | None,
    ) -> ScheduleEventFullDTO:
        # queue is passed in explicitly: single-row reads supply the undeferred
        # column_property value, while the list query supplies it from its single
        # joined ranking subquery.
        return ScheduleEventFullDTO(
            id=ScheduleEventId(event_orm.id),
            number=event_orm.number,
            title=event_orm.title,
            duration=event_orm.duration,
            order=event_orm.order,
            is_current=event_orm.is_current,
            is_skipped=event_orm.is_skipped,
            nomination_title=event_orm.nomination_title,
            block_title=event_orm.block_title,
            queue=queue,
        )
