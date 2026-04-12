from pydantic import BaseModel

from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.push_subscriptions import (
    PushSubscriptionRepository,
)
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.push_sub import PushSubNotFound


class DeletePushSubscriptionInput(BaseModel):
    endpoint: str


class DeletePushSubscription:
    def __init__(
        self,
        push_sub_repo: PushSubscriptionRepository,
        id_provider: IdProvider,
        trx: TransactionManager,
    ) -> None:
        self.trx = trx
        self.id_provider = id_provider
        self.push_sub_repo = push_sub_repo

    async def __call__(self, data: DeletePushSubscriptionInput) -> None:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        push_sub = await self.push_sub_repo.get_by_endpoint(data.endpoint)
        if push_sub is None:
            raise PushSubNotFound
        if push_sub.user_id != current_user_id:
            raise AccessDenied
        await self.push_sub_repo.delete(push_sub)
        await self.trx.commit()
