from pydantic import BaseModel

from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.push_sub import PushSubscriptionNotFound


class DeletePushSubscriptionInput(BaseModel):
    endpoint: str


class DeletePushSubscription:
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ) -> None:
        self.uow = uow
        self.current_user_provider = current_user_provider
        self.push_sub_gateway = push_sub_gateway

    async def __call__(self, data: DeletePushSubscriptionInput) -> None:
        current_user_id = await self.current_user_provider.require_user_id()
        push_sub = await self.push_sub_gateway.get_by_endpoint(data.endpoint)
        if push_sub is None:
            raise PushSubscriptionNotFound
        if push_sub.user_id != current_user_id:
            raise AccessDenied
        await self.push_sub_gateway.delete(push_sub)
        await self.uow.commit()
