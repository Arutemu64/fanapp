from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.push_subscriptions import (
    PushSubscriptionRepository,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.models.push_subscription import PushSubscription


class CreatePushSubscriptionInput(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class CreatePushSubscription:
    def __init__(
        self,
        push_sub_repo: PushSubscriptionRepository,
        user_repo: UserRepository,
        id_provider: IdProvider,
        trx: TransactionManager,
    ):
        self.user_repo = user_repo
        self.push_sub_repo = push_sub_repo
        self.id_provider = id_provider
        self.trx = trx

    async def __call__(self, data: CreatePushSubscriptionInput) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        push_subscription = PushSubscription(
            user_id=current_user.id,
            endpoint=data.endpoint,
            p256dh=data.p256dh,
            auth=data.auth,
        )
        await self.push_sub_repo.add(push_subscription)
        await self.trx.commit()
