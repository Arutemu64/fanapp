from pydantic import BaseModel

from fanfan.adapters.db.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.push_notification import PushSubscription


class CreatePushSubscriptionCommand(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class CreatePushSubscription:
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.push_sub_gateway = push_sub_gateway
        self.id_provider = id_provider
        self.uow = uow

    async def __call__(self, data: CreatePushSubscriptionCommand) -> None:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            push_subscription = PushSubscription(
                user_id=current_user.id,
                endpoint=data.endpoint,
                p256dh=data.p256dh,
                auth=data.auth,
            )
            await self.push_sub_gateway.add_push_subscription(push_subscription)
            await self.uow.commit()
