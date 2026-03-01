from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.models.push_notification import PushSubscription
from fanfan.core.vo.push_subscription import PushSubscriptionId
from fanfan.core.vo.user import UserId


class PushSubscriptionORM(BaseORM):
    __tablename__ = "push_subscription"

    id: Mapped[PushSubscriptionId] = mapped_column(primary_key=True)
    user_id: Mapped[UserId] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    endpoint: Mapped[str] = mapped_column(unique=True)
    p256dh: Mapped[str] = mapped_column()
    auth: Mapped[str] = mapped_column()

    def to_model(self) -> PushSubscription:
        return PushSubscription(
            id=self.id,
            user_id=self.user_id,
            endpoint=self.endpoint,
            p256dh=self.p256dh,
            auth=self.auth,
        )

    @classmethod
    def from_model(cls, model: PushSubscription) -> PushSubscriptionORM:
        return PushSubscriptionORM(
            id=model.id,
            user_id=model.user_id,
            endpoint=model.endpoint,
            p256dh=model.p256dh,
            auth=model.auth,
        )
