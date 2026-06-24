from fanfan.adapters.db.models import SubscriptionORM
from fanfan.application.dto.subscription import (
    SubscriptionFullDTO,
    SubscriptionScheduleItemDTO,
)
from fanfan.core.models.subscription import Subscription
from fanfan.core.vo.schedule_item import ScheduleItemId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionMapper:
    @staticmethod
    def from_model(model: Subscription) -> SubscriptionORM:
        return SubscriptionORM(
            id=model.id,
            user_id=model.user_id,
            schedule_item_id=model.schedule_item_id,
            counter=model.counter,
        )

    @staticmethod
    def to_model(orm: SubscriptionORM) -> Subscription:
        return Subscription(
            id=SubscriptionId(orm.id),
            user_id=UserId(orm.user_id),
            schedule_item_id=ScheduleItemId(orm.schedule_item_id),
            counter=orm.counter,
        )

    @staticmethod
    def parse_full_dto(
        subscription_orm: SubscriptionORM,
    ) -> SubscriptionFullDTO:
        return SubscriptionFullDTO(
            id=SubscriptionId(subscription_orm.id),
            user_id=UserId(subscription_orm.user_id),
            counter=subscription_orm.counter,
            schedule_item=SubscriptionScheduleItemDTO(
                id=ScheduleItemId(subscription_orm.schedule_item.id),
                number=subscription_orm.schedule_item.number,
                title=subscription_orm.schedule_item.title,
                order=subscription_orm.schedule_item.order,
                queue=subscription_orm.schedule_item.queue,
                time_until=subscription_orm.schedule_item.time_until,
            ),
        )
