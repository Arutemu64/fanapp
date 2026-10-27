from pydantic import BaseModel, Field

from fanfan.application.dto.input import InputModel
from fanfan.application.interactors.push_sub.create_push_subscription import (
    PUSH_ENDPOINT_MAX_LENGTH,
)
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.services.current_user import CurrentUserProvider


class CheckPushSubscriptionInput(InputModel):
    endpoint: str = Field(max_length=PUSH_ENDPOINT_MAX_LENGTH)


class CheckPushSubscriptionOutput(BaseModel):
    subscribed: bool


class CheckPushSubscription:
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.push_sub_gateway = push_sub_gateway

    async def __call__(
        self, data: CheckPushSubscriptionInput
    ) -> CheckPushSubscriptionOutput:
        current_user_id = await self.current_user_provider.require_user_id()
        subscribed = await self.push_sub_gateway.exists_for_user(
            current_user_id, data.endpoint
        )
        return CheckPushSubscriptionOutput(subscribed=subscribed)
