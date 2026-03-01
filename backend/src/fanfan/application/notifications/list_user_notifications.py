from pydantic import BaseModel

from fanfan.adapters.db.gateways.notifications import NotificationGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.notification import NotificationDTO
from fanfan.core.dto.page import Pagination
from fanfan.core.exceptions.auth import UserNotAuthenticated


class ListUserNotificationsCommand(BaseModel):
    pagination: Pagination


class ListUserNotificationsResult(BaseModel):
    notifications: list[NotificationDTO]


class ListUserNotifications:
    def __init__(
        self, notification_gateway: NotificationGateway, id_provider: IdProvider
    ):
        self.notification_gateway = notification_gateway
        self.id_provider = id_provider

    async def __call__(
        self, data: ListUserNotificationsCommand
    ) -> ListUserNotificationsResult:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated

        notifications = await self.notification_gateway.read_list_user_notifications(
            user_id=current_user_id,
            pagination=data.pagination,
        )

        return ListUserNotificationsResult(notifications=notifications)
