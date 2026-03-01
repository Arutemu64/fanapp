from pydantic import BaseModel

from fanfan.adapters.db.gateways.push_subscriptions import PushSubscriptionGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied


class DeletePushSubscriptionCommand(BaseModel):
    endpoint: str


class DeletePushSubscription:
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        id_provider: IdProvider,
        uow: UnitOfWork,
    ) -> None:
        self.uow = uow
        self.id_provider = id_provider
        self.push_sub_gateway = push_sub_gateway

    async def __call__(self, data: DeletePushSubscriptionCommand) -> None:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        async with self.uow:
            push_sub = await self.push_sub_gateway.get_push_sub_by_endpoint(
                data.endpoint
            )
            if push_sub.user_id != current_user_id:
                raise AccessDenied
            await self.push_sub_gateway.delete_push_subscription(push_sub)
            await self.uow.commit()
        return
