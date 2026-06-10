from pydantic import BaseModel

from fanfan.application.dto.notification import NotificationDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.repositories.notifications import NotificationRepository
from fanfan.application.services.current_user import CurrentUserProvider


class ListUserNotificationsInput(BaseModel):
    pagination: Pagination


class ListUserNotificationOutput(BaseModel):
    notifications: list[NotificationDTO]


class ListUserNotifications:
    def __init__(
        self,
        notification_query: NotificationRepository,
        current_user_provider: CurrentUserProvider,
    ):
        self.notification_query = notification_query
        self.current_user_provider = current_user_provider

    async def __call__(
        self, data: ListUserNotificationsInput
    ) -> ListUserNotificationOutput:
        current_user_id = await self.current_user_provider.require_user_id()

        notifications = await self.notification_query.read_list_user_notifications(
            user_id=current_user_id,
            pagination=data.pagination,
        )

        return ListUserNotificationOutput(notifications=notifications)
