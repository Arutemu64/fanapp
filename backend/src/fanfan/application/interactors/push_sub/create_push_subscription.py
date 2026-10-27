from pydantic import BaseModel, Field

from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.push_subscription import generate_push_subscription_id

PUSH_ENDPOINT_MAX_LENGTH = 2048
PUSH_KEY_MAX_LENGTH = 256


class CreatePushSubscriptionInput(BaseModel):
    endpoint: str = Field(max_length=PUSH_ENDPOINT_MAX_LENGTH)
    p256dh: str = Field(max_length=PUSH_KEY_MAX_LENGTH)
    auth: str = Field(max_length=PUSH_KEY_MAX_LENGTH)


class CreatePushSubscription:
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ) -> None:
        self.user_gateway = user_gateway
        self.push_sub_gateway = push_sub_gateway
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
        await self.push_sub_gateway.add(push_subscription)
        await self.uow.commit()
