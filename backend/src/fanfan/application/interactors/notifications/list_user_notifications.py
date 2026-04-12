from pydantic import BaseModel

from fanfan.application.dto.notification import NotificationDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.notifications import NotificationRepository
from fanfan.core.exceptions.auth import UserNotAuthenticated


class ListUserNotificationsInput(BaseModel):
    pagination: Pagination


class ListUserNotificationOutput(BaseModel):
    notifications: list[NotificationDTO]


class ListUserNotifications:
    def __init__(
        self, notification_repo: NotificationRepository, id_provider: IdProvider
    ):
        self.notification_repo = notification_repo
        self.id_provider = id_provider

    async def __call__(
        self, data: ListUserNotificationsInput
    ) -> ListUserNotificationOutput:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated

        notifications = await self.notification_repo.read_list_user_notifications(
            user_id=current_user_id,
            pagination=data.pagination,
        )

        return ListUserNotificationOutput(notifications=notifications)
