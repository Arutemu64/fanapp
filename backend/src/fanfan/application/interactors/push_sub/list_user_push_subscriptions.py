from fanfan.application.dto.push_sub import PushSubscriptionDTO
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.services.current_user import CurrentUserProvider


class ListUserPushSubscriptions:
    # TODO Do I need this?
    def __init__(
        self,
        push_sub_gateway: PushSubscriptionGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.push_sub_gateway = push_sub_gateway

    async def __call__(self) -> list[PushSubscriptionDTO]:
        current_user_id = await self.current_user_provider.require_user_id()
        push_subs = await self.push_sub_gateway.list_by_user(current_user_id)
        return [
            PushSubscriptionDTO(
                endpoint=sub.endpoint,
                p256dh=sub.p256dh,
                auth=sub.auth,
            )
            for sub in push_subs
        ]
