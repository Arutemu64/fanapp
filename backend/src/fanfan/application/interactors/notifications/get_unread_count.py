from pydantic import BaseModel

from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.services.current_user import CurrentUserProvider


class UnreadNotificationsCountOutput(BaseModel):
    count: int


class GetUnreadNotificationsCount:
    def __init__(
        self,
        notification_gateway: NotificationGateway,
        current_user_provider: CurrentUserProvider,
    ):
        self.notification_gateway = notification_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self) -> UnreadNotificationsCountOutput:
        current_user_id = await self.current_user_provider.require_user_id()
        count = await self.notification_gateway.count_unread_for_user(
            user_id=current_user_id,
        )
        return UnreadNotificationsCountOutput(count=count)
