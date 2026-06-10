from fanfan.adapters.db.models import SubscriptionORM
from fanfan.application.dto.subscription import (
    SubscriptionEventDTO,
    SubscriptionFullDTO,
)
from fanfan.core.models.subscription import Subscription
from fanfan.core.vo.schedule_event import ScheduleEventId, ScheduleEventPublicNumber
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


class SubscriptionMapper:
    @staticmethod
    def from_model(model: Subscription) -> SubscriptionORM:
        return SubscriptionORM(
            id=model.id,
            user_id=model.user_id,
            event_id=model.event_id,
            counter=model.counter,
        )

    @staticmethod
    def to_model(orm: SubscriptionORM) -> Subscription:
        return Subscription(
            id=SubscriptionId(orm.id),
            user_id=UserId(orm.user_id),
            event_id=ScheduleEventId(orm.event_id),
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
            event=SubscriptionEventDTO(
                id=ScheduleEventId(subscription_orm.event.id),
                public_number=ScheduleEventPublicNumber(
                    subscription_orm.event.public_id
                ),
                title=subscription_orm.event.title,
                order=subscription_orm.event.order,
                queue=subscription_orm.event.queue,
                time_until=subscription_orm.event.time_until,
            ),
        )
