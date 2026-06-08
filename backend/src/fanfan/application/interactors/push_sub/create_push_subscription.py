from pydantic import BaseModel

from fanfan.application.ports.repositories.push_subscriptions import (
    PushSubscriptionRepository,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.push_subscription import generate_push_subscription_id


class CreatePushSubscriptionInput(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class CreatePushSubscription:
    def __init__(
        self,
        push_sub_repo: PushSubscriptionRepository,
        user_repo: UserRepository,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ):
        self.user_repo = user_repo
        self.push_sub_repo = push_sub_repo
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: CreatePushSubscriptionInput) -> None:
        current_user = await self.current_user_provider.require_user()
        push_subscription = PushSubscription(
            id=generate_push_subscription_id(),
            user_id=current_user.id,
            endpoint=data.endpoint,
            p256dh=data.p256dh,
            auth=data.auth,
        )
        await self.push_sub_repo.add(push_subscription)
        await self.uow.commit()
