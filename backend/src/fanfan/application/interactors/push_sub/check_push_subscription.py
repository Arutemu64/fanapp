from pydantic import BaseModel

from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.services.current_user import CurrentUserProvider


class CheckPushSubscriptionInput(BaseModel):
    endpoint: str


class CheckPushSubscription:
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.push_sub_gateway = push_sub_gateway

    async def __call__(self, data: CheckPushSubscriptionInput) -> bool:
        current_user_id = await self.current_user_provider.require_user_id()
        return await self.push_sub_gateway.exists_for_user(
            current_user_id, data.endpoint
        )
