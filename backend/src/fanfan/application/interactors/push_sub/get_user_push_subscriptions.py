from fanfan.application.dto.push_sub import PushSubscriptionDTO
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.push_subscriptions import (
    PushSubscriptionRepository,
)
from fanfan.core.exceptions.auth import UserNotAuthenticated


class ListUserPushSubscriptions:
    # TODO Do I need this?
    def __init__(
        self, push_sub_repo: PushSubscriptionRepository, id_provider: IdProvider
    ) -> None:
        self.id_provider = id_provider
        self.push_sub_repo = push_sub_repo

    async def __call__(self) -> list[PushSubscriptionDTO]:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        push_subs = await self.push_sub_repo.list_by_user(current_user_id)
        return [
            PushSubscriptionDTO(
                endpoint=sub.endpoint,
                p256dh=sub.p256dh,
                auth=sub.auth,
            )
            for sub in push_subs
        ]
