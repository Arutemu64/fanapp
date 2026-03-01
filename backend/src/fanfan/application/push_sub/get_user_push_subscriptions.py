from fanfan.adapters.db.gateways.push_subscriptions import PushSubscriptionGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.push_sub import PushSubscriptionDTO
from fanfan.core.exceptions.auth import UserNotAuthenticated


class ListUserPushSubscriptions:
    def __init__(
        self, push_sub_gateway: PushSubscriptionGateway, id_provider: IdProvider
    ) -> None:
        self.id_provider = id_provider
        self.push_sub_gateway = push_sub_gateway

    async def __call__(self) -> list[PushSubscriptionDTO]:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        push_subs = await self.push_sub_gateway.list_user_push_subs(current_user_id)
        return [
            PushSubscriptionDTO(
                endpoint=sub.endpoint,
                p256dh=sub.p256dh,
                auth=sub.auth,
            )
            for sub in push_subs
        ]
