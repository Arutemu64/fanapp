from fanfan.adapters.db.models import PushSubscriptionORM
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.push_subscription import PushSubscriptionId
from fanfan.core.vo.user import UserId


class PushSubscriptionMapper:
    @staticmethod
    def from_model(model: PushSubscription) -> PushSubscriptionORM:
        return PushSubscriptionORM(
            id=model.id,
            user_id=model.user_id,
            endpoint=model.endpoint,
            p256dh=model.p256dh,
            auth=model.auth,
        )

    @staticmethod
    def to_model(orm: PushSubscriptionORM) -> PushSubscription:
        return PushSubscription(
            id=PushSubscriptionId(orm.id),
            user_id=UserId(orm.user_id),
            endpoint=orm.endpoint,
            p256dh=orm.p256dh,
            auth=orm.auth,
        )
