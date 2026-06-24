from fanfan.adapters.db.models import ScheduleItemORM
from fanfan.application.dto.schedule import ScheduleItemFullDTO
from fanfan.core.models.schedule_item import ScheduleItem
from fanfan.core.vo.schedule_item import ScheduleItemId


class ScheduleItemMapper:
    @staticmethod
    def from_model(model: ScheduleItem):
        return ScheduleItemORM(
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
    def to_model(orm: ScheduleItemORM) -> ScheduleItem:
        return ScheduleItem(
            id=ScheduleItemId(orm.id),
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
        event_orm: ScheduleItemORM,
        *,
        queue: int | None,
        time_until: int | None,
    ) -> ScheduleItemFullDTO:
        # queue/time_until are passed in explicitly: single-row reads supply the
        # undeferred column_property values, while the list query supplies the
        # columns from its single joined ranking subquery.
        return ScheduleItemFullDTO(
            id=ScheduleItemId(event_orm.id),
            number=event_orm.number,
            title=event_orm.title,
            duration=event_orm.duration,
            order=event_orm.order,
            is_current=event_orm.is_current,
            is_skipped=event_orm.is_skipped,
            nomination_title=event_orm.nomination_title,
            block_title=event_orm.block_title,
            queue=queue,
            time_until=time_until,
        )
