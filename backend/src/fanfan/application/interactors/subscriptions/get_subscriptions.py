from pydantic import BaseModel

from fanfan.application.dto.subscription import SubscriptionFullDTO
from fanfan.application.ports.gateways.subscriptions import (
    SubscriptionGateway,
)
from fanfan.application.services.current_user import CurrentUserProvider


class GetSubscriptionsOutput(BaseModel):
    subscriptions: list[SubscriptionFullDTO]


class GetSubscriptions:
    def __init__(
        self,
        subscription_gateway: SubscriptionGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.subscription_gateway = subscription_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self) -> GetSubscriptionsOutput:
        current_user_id = await self.current_user_provider.require_user_id()
        subscriptions = await self.subscription_gateway.read_subscriptions_by_user(
            current_user_id
        )
        return GetSubscriptionsOutput(subscriptions=subscriptions)
