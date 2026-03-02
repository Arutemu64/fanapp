from fanfan.adapters.db.models import SubscriptionORM
from fanfan.core.dto.subscription import SubscriptionEventDTO, SubscriptionFullDTO
from fanfan.core.models.subscription import Subscription


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
            id=orm.id,
            user_id=orm.user_id,
            event_id=orm.event_id,
            counter=orm.counter,
        )

    @staticmethod
    def parse_full_dto(
        subscription_orm: SubscriptionORM,
    ) -> SubscriptionFullDTO:
        return SubscriptionFullDTO(
            id=subscription_orm.id,
            user_id=subscription_orm.user_id,
            counter=subscription_orm.counter,
            event=SubscriptionEventDTO(
                id=subscription_orm.event.id,
                public_number=subscription_orm.event.public_id,
                title=subscription_orm.event.title,
                order=subscription_orm.event.order,
                queue=subscription_orm.event.queue,
                time_until=subscription_orm.event.time_until,
            )
            if subscription_orm.event
            else None,
        )
